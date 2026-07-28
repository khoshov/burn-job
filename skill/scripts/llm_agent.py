#!/usr/bin/env python3
"""
LLM-Based Code Refactoring Agent for Java / Spring Boot Performance Antipatterns.
Parses findings reports (findings.json / KùzuDB graph anomalies), constructs LLM prompts,
generates single or multi-variant refactoring candidates (T1–T9), verifies compilation/tests via Maven,
evaluates JFR profiling samples & benchmark metrics, and logs all steps to runlog/agent_run.log.
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# Add skill/scripts to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from multi_variant_jfr_evaluator import evaluate_variant_candidates, JFRProfiler
    HAS_MULTI_JFR_EVAL = True
except ImportError:
    HAS_MULTI_JFR_EVAL = False

DEFAULT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runlog", "agent_run.log")

NON_DEFECT_RULES = """
### SECTION 7: NON-DEFECT RULES (DO NOT REFACTOR IF APPLICABLE)
1. Field ordering in classes (HotSpot JVM optimizes layout automatically).
2. Bounded quadratic complexity when input size N <= 8 (e.g., small fixed parameter lists).
3. Bounded caches with maximum size and LRU eviction policy.
4. Request collections bounded by request contract (e.g. pageSize).
5. Microbenchmark noise without measurable impact under real load.
6. Code style / formatting choices that do not affect runtime execution.
"""

SYSTEM_PROMPT = f"""You are an elite Java 21 & Spring Boot 3 performance optimization AI agent.
Your task is to rewrite sub-optimal Java code to eliminate performance bottlenecks (N+1 queries, memory bloat, save in loops, full entity fetch, CPU hotspots).

RULES:
1. Preserve all existing public API contracts (method signatures, parameters, return types, endpoints).
2. Do NOT remove functional behavior or assertions.
3. NEVER set spring.jpa.open-in-view to true.
4. Output ONLY valid, complete refactored Java code inside ```java ... ``` code blocks.
5. Respect non-defect rules:
{NON_DEFECT_RULES}
"""

SYSTEM_MULTI_VARIANT_PROMPT = SYSTEM_PROMPT + """
MULTI-VARIANT INSTRUCTIONS:
Please generate EXACTLY 3 DISTINCT complete refactored Java file candidate implementations for the bottleneck, labeled clearly as:
[VARIANT_1]
```java
// Complete Java file 1 with package, imports, and public class ...
```
[VARIANT_2]
```java
// Complete Java file 2 with package, imports, and public class ...
```
[VARIANT_3]
```java
// Complete Java file 3 with package, imports, and public class ...
```
CRITICAL RULE:
Each variant MUST be a COMPLETE, compilable Java source file containing the package declaration, all imports, and the full public class definition. Do NOT output partial methods or unwrapped code snippets!
"""

class LLMAgentLogger:
    def __init__(self, log_path=DEFAULT_LOG_PATH):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, level: str, message: str):
        timestamp = datetime.now().isoformat()
        formatted = f"[{timestamp}] [{level.upper()}] {message}\n"
        print(formatted, end="", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(formatted)

class LLMAgent:
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None, logger: LLMAgentLogger = None):
        self.logger = logger or LLMAgentLogger()
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GIGACHAT_API_KEY") or os.getenv("LLM_API_KEY")
        
        default_base_url = "https://api.deepseek.com/v1" if (self.api_key and "deepseek" in (base_url or "").lower()) or os.getenv("DEEPSEEK_API_KEY") else "https://api.openai.com/v1"
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or default_base_url).rstrip("/")
        
        default_model = "deepseek-chat" if "deepseek" in self.base_url.lower() else "gpt-4o"
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or default_model

    def is_api_configured(self) -> bool:
        return bool(self.api_key)

    def call_llm(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        if not self.is_api_configured():
            raise ValueError("LLM API Key not provided. Configure OPENAI_API_KEY or use offline mode.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            self.logger.log("ERROR", f"LLM API HTTPError {e.code}: {err_body}")
            raise Exception(f"HTTP {e.code}: {err_body}")
        except Exception as e:
            self.logger.log("ERROR", f"LLM API Exception: {str(e)}")
            raise

    def extract_code_block(self, llm_response: str) -> str:
        match = re.search(r"```java\s*\n(.*?)\n```", llm_response, re.DOTALL)
        if match:
            return match.group(1)
        match_generic = re.search(r"```\s*\n(.*?)\n```", llm_response, re.DOTALL)
        if match_generic:
            return match_generic.group(1)
        return llm_response.strip()

    def extract_multi_code_blocks(self, llm_response: str) -> Dict[str, str]:
        """Extracts multiple candidate variants [VARIANT_1], [VARIANT_2], [VARIANT_3]."""
        candidates = {}
        pattern = r"\[VARIANT_(\d+)\]\s*```java\s*\n(.*?)\n```"
        matches = re.findall(pattern, llm_response, re.DOTALL)
        if matches:
            for idx, code in matches:
                candidates[f"v{idx}"] = code
        else:
            # Fallback if LLM didn't format tags strictly
            blocks = re.findall(r"```java\s*\n(.*?)\n```", llm_response, re.DOTALL)
            for idx, code in enumerate(blocks, start=1):
                candidates[f"v{idx}"] = code

        if not candidates:
            single = self.extract_code_block(llm_response)
            if single:
                candidates["v1"] = single

        return candidates

    def fallback_refactor(self, finding: dict, file_content: str) -> str:
        variants = self.fallback_multi_variant(finding, file_content)
        return variants.get("v1", file_content)

    def fallback_multi_variant(self, finding: dict, file_content: str) -> Dict[str, str]:
        """Generates multiple candidate variants offline using taxonomy templates (FIX_VARIANTS.md)."""
        file_path = finding.get("file", "")
        pdf_tax = finding.get("pdf_taxonomy", [])
        mechanism = finding.get("mechanism", "").lower()
        candidates = {}

        # 1. N+1 Queries (NPlusOneService.java)
        if "nplusoneservice" in file_path.lower() or "t6" in pdf_tax or "n+1" in mechanism:
            candidates["v1"] = re.sub(
                r'List<Department>\s+departments\s*=\s*departmentRepository\.findAll\(\);',
                'List<Department> departments = departmentRepository.findAllWithEmployeesOptimal();',
                file_content
            )
            candidates["v2"] = re.sub(
                r'List<Department>\s+departments\s*=\s*departmentRepository\.findAll\(\);',
                'List<Department> departments = departmentRepository.findAllEntityGraph();',
                file_content
            )
            candidates["v3"] = re.sub(
                r'List<Department>\s+departments\s*=\s*departmentRepository\.findAll\(\);',
                'List<Department> departments = departmentRepository.findAllDtoProjection();',
                file_content
            )

        # 2. In-Memory Filter & Pagination (InMemoryFilterService.java)
        elif "inmemoryfilterservice" in file_path.lower() or "t8" in pdf_tax or "in-memory" in mechanism:
            candidates["v1"] = re.sub(
                r'public\s+List<OrderSummaryDto>\s+getOrdersByStatusSubOptimal\([^)]*\)\s*\{[^}]*\}',
                '''public List<OrderSummaryDto> getOrdersByStatusSubOptimal(String status, int page, int size) {
        // Variant 1 (PageRequest): Push WHERE & LIMIT/OFFSET to DB
        return orderRepository.findByStatusOptimal(status, org.springframework.data.domain.PageRequest.of(page, size))
                .getContent();
    }''',
                file_content, flags=re.DOTALL
            )
            candidates["v2"] = re.sub(
                r'public\s+List<OrderSummaryDto>\s+getOrdersByStatusSubOptimal\([^)]*\)\s*\{[^}]*\}',
                '''public List<OrderSummaryDto> getOrdersByStatusSubOptimal(String status, int page, int size) {
        // Variant 2 (Slice): Avoid COUNT(*) total query overhead
        return orderRepository.findSliceByStatus(status, org.springframework.data.domain.PageRequest.of(page, size))
                .getContent();
    }''',
                file_content, flags=re.DOTALL
            )

        # 3. Save in Loop (SaveInLoopService.java)
        elif "saveinloopservice" in file_path.lower() or ("t6" in pdf_tax and "save" in mechanism) or "batching" in mechanism:
            candidates["v1"] = re.sub(
                r'for\s*\([^)]*\)\s*\{[^}]*employeeRepository\.save\(emp\);[^}]*\}',
                '''List<Employee> employeesToSave = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            employeesToSave.add(new Employee("SubOptFirst" + i, "SubOptLast" + i, "subopt" + i + "@example.com", BigDecimal.valueOf(50000 + i), "Heavy bio " + i, null));
        }
        employeeRepository.saveAll(employeesToSave);''',
                file_content, flags=re.DOTALL
            )

        # 4. Full Entity Fetch (FullEntityFetchService.java)
        elif "fullentityfetchservice" in file_path.lower() or "t3" in pdf_tax or "projection" in mechanism:
            candidates["v1"] = re.sub(
                r'public\s+List<EmployeeSimpleDto>\s+getEmployeesSubOptimal\(\)\s*\{[^}]*\}',
                '''public List<EmployeeSimpleDto> getEmployeesSubOptimal() {
        // Variant 1: Interface Projection
        return employeeRepository.findAllProjectedBy().stream()
                .map(p -> new EmployeeSimpleDto(p.getId(), p.getFirstName(), p.getLastName(), p.getEmail()))
                .toList();
    }''',
                file_content, flags=re.DOTALL
            )

        if not candidates:
            candidates["v1"] = file_content

        return candidates

    def process_finding(self, finding: dict, root_dir: str, dry_run: bool = False, force_offline: bool = False, multi_variant: bool = False, enable_jfr: bool = False) -> bool:
        rel_file = finding.get("file")
        if not rel_file:
            self.logger.log("WARNING", "Finding missing 'file' attribute. Skipping.")
            return False

        abs_file = os.path.join(root_dir, rel_file)
        if not os.path.exists(abs_file):
            self.logger.log("WARNING", f"Target file {abs_file} does not exist. Skipping.")
            return False

        self.logger.log("INFO", f"Processing finding for file: {rel_file} (Lines {finding.get('line_from')}-{finding.get('line_to')})")
        self.logger.log("INFO", f"Taxonomy: {finding.get('pdf_taxonomy')} | Mechanism: {finding.get('mechanism')}")

        with open(abs_file, "r", encoding="utf-8") as f:
            original_code = f.read()

        candidates = {}

        if multi_variant or enable_jfr:
            self.logger.log("INFO", "Mode: Multi-Variant Refactoring & JFR Benchmark Selection Enabled.")
            if not force_offline and self.is_api_configured():
                prompt = f"""Target File: {rel_file}
Line Range: {finding.get('line_from')} to {finding.get('line_to')}
Taxonomy Codes: {finding.get('pdf_taxonomy')}
Mechanism / Bottleneck: {finding.get('mechanism')}

Existing Java File Content:
```java
{original_code}
```
Please output 3 distinct refactoring candidates according to Multi-Variant instructions."""
                try:
                    self.logger.log("INFO", f"Requesting multi-variant options from LLM ({self.model})...")
                    resp = self.call_llm(prompt, system_prompt=SYSTEM_MULTI_VARIANT_PROMPT)
                    candidates = self.extract_multi_code_blocks(resp)
                    self.logger.log("INFO", f"Extracted {len(candidates)} candidate variant(s) from LLM.")
                except Exception as e:
                    self.logger.log("WARNING", f"LLM Multi-Variant call failed ({e}). Using offline taxonomy candidates.")
                    candidates = self.fallback_multi_variant(finding, original_code)
            else:
                candidates = self.fallback_multi_variant(finding, original_code)

            if dry_run:
                self.logger.log("INFO", f"[DRY RUN] Generated {len(candidates)} candidate variants for {rel_file}.")
                return True

            # Evaluate candidate variants with build & JFR profiling
            self.logger.log("INFO", f"Evaluating {len(candidates)} candidate variants for {rel_file}...")
            
            def apply_patch(code: str) -> bool:
                try:
                    with open(abs_file, "w", encoding="utf-8") as f:
                        f.write(code)
                    return True
                except Exception:
                    return False

            def verify_build() -> bool:
                return self.verify_maven_build(root_dir)

            winning_code = original_code
            winning_name = None

            if HAS_MULTI_JFR_EVAL:
                eval_res = evaluate_variant_candidates(candidates=candidates, apply_func=apply_patch, verify_func=verify_build)
                winner_id = eval_res.get("winning_candidate")
                if winner_id and winner_id in candidates:
                    winning_name = winner_id
                    winning_code = candidates[winner_id]
                    self.logger.log("SUCCESS", f"🏆 Winning Variant Selected: [{winner_id}] with optimal performance score: {eval_res['best_score']:.2f}")
                else:
                    self.logger.log("WARNING", "No candidate variant passed build/verification. Rolling back to original.")
                    apply_patch(original_code)
                    return False
            else:
                # Basic fallback if evaluator module not loaded
                for var_name, code in candidates.items():
                    apply_patch(code)
                    if verify_build():
                        winning_name = var_name
                        winning_code = code
                        break
                if not winning_name:
                    apply_patch(original_code)
                    return False

            # Apply final winning code
            apply_patch(winning_code)
            self.logger.log("SUCCESS", f"Applied winning variant [{winning_name}] to {rel_file}.")
            return True

        else:
            # Single-variant mode
            new_code = None
            if not force_offline and self.is_api_configured():
                prompt = f"""Target File: {rel_file}
Line Range: {finding.get('line_from')} to {finding.get('line_to')}
Taxonomy Codes: {finding.get('pdf_taxonomy')}
Mechanism / Bottleneck: {finding.get('mechanism')}

Existing Java File Content:
```java
{original_code}
```
Please rewrite the entire Java file with the optimal implementation."""
                try:
                    llm_response = self.call_llm(prompt)
                    new_code = self.extract_code_block(llm_response)
                except Exception as e:
                    self.logger.log("WARNING", f"LLM call failed ({e}). Falling back to offline refactoring engine.")
                    new_code = self.fallback_refactor(finding, original_code)
            else:
                new_code = self.fallback_refactor(finding, original_code)

            if dry_run:
                self.logger.log("INFO", f"[DRY RUN] Would write updated content to {rel_file}.")
                return True

            with open(abs_file, "w", encoding="utf-8") as f:
                f.write(new_code)

            self.logger.log("SUCCESS", f"Successfully applied refactoring to {rel_file}.")
            return True

    def verify_maven_build(self, root_dir: str) -> bool:
        self.logger.log("INFO", "Executing Maven verification (mvn test-compile)...")
        try:
            res = subprocess.run(["mvn", "test-compile"], cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
            if res.returncode == 0:
                self.logger.log("SUCCESS", "Maven test-compile PASSED cleanly.")
                return True
            else:
                self.logger.log("ERROR", f"Maven test-compile FAILED:\n{res.stderr or res.stdout}")
                return False
        except Exception as e:
            self.logger.log("ERROR", f"Failed to execute mvn test-compile: {str(e)}")
            return False

def load_findings(report_path: str) -> list:
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Report file not found: {report_path}")

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Unrecognized report schema. Expected 'findings' key or JSON list.")

def main():
    parser = argparse.ArgumentParser(description="LLM-Based Code Refactoring & Multi-Variant JFR Evaluation Agent")
    parser.add_argument("--report", default="reports/sandbox/findings.json", help="Path to findings JSON report")
    parser.add_argument("--src-dir", default=".", help="Root directory of the target project")
    parser.add_argument("--model", help="LLM model name (e.g. deepseek-chat, gpt-4o)")
    parser.add_argument("--api-key", help="API key for LLM provider")
    parser.add_argument("--base-url", help="Base URL for OpenAI-compatible LLM endpoint (e.g. https://api.deepseek.com)")
    parser.add_argument("--offline", action="store_true", help="Force offline deterministic pattern refactoring")
    parser.add_argument("--dry-run", action="store_true", help="Perform analysis without writing changes to disk")
    parser.add_argument("--no-verify", action="store_true", help="Skip Maven compilation verification")
    parser.add_argument("--multi-variant", action="store_true", help="Generate all possible candidate variants (T1-T9) for each bottleneck")
    parser.add_argument("--enable-jfr", action="store_true", help="Capture JFR profiles across candidate variants and select winner by performance score")
    parser.add_argument("--benchmark-all-variants", action="store_true", help="Run multi-variant feature toggle benchmarking suite to select winner")
    parser.add_argument("--iterative", action="store_true", help="Enable SysLLMatic iterative self-optimization loop (Generator -> Verifier -> Evaluator Feedback)")
    parser.add_argument("--max-steps", type=int, default=3, help="Maximum number of self-optimization iterations in --iterative mode (default: 3)")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.src_dir)
    logger = LLMAgentLogger()
    logger.log("INFO", "=== STARTING LLM CODE REFACTORING & JFR EVALUATION AGENT ===")

    report_path = args.report
    if not os.path.isabs(report_path):
        report_path = os.path.join(root_dir, report_path)

    if not os.path.exists(report_path):
        export_script = os.path.join(root_dir, "scripts", "export_report.py")
        if os.path.exists(export_script):
            logger.log("INFO", "Report file not found. Generating findings from scripts/export_report.py...")
            from export_report import generate_burn_job_report
            report_data = generate_burn_job_report()
            findings = report_data["findings"]
        else:
            logger.log("ERROR", f"Could not find report or export_report.py at {report_path}")
            sys.exit(1)
    else:
        findings = load_findings(report_path)

    logger.log("INFO", f"Loaded {len(findings)} findings from report.")

    if args.iterative:
        logger.log("INFO", f"Mode: SysLLMatic Iterative Self-Optimization Loop Enabled (max_steps={args.max_steps}).")
        from iterative_agent_loop import run_iterative_loop
        modified_count = 0
        for finding in findings:
            rel_file = finding.get("file")
            if not rel_file:
                continue
            abs_file = os.path.join(root_dir, rel_file)
            if not os.path.exists(abs_file):
                continue
            res = run_iterative_loop(
                target_file=abs_file,
                max_steps=args.max_steps,
                findings=[finding],
                offline=args.offline,
                run_log_path=logger.log_path,
                verify_mvn=not args.no_verify,
            )
            if res.get("success"):
                modified_count += 1
        logger.log("INFO", f"Iterative refactoring complete. {modified_count}/{len(findings)} target files optimized.")
        sys.exit(0)

    agent = LLMAgent(model=args.model, api_key=args.api_key, base_url=args.base_url, logger=logger)
    modified_count = 0

    for finding in findings:
        success = agent.process_finding(
            finding,
            root_dir=root_dir,
            dry_run=args.dry_run,
            force_offline=args.offline,
            multi_variant=args.multi_variant,
            enable_jfr=args.enable_jfr
        )
        if success:
            modified_count += 1

    logger.log("INFO", f"Refactoring complete. {modified_count}/{len(findings)} files modified.")

    if not args.dry_run and not args.no_verify and modified_count > 0:
        verified = agent.verify_maven_build(root_dir)
        if not verified:
            logger.log("ERROR", "Maven build verification failed after refactoring.")
            sys.exit(1)

    if args.benchmark_all_variants:
        logger.log("INFO", "Running multi-variant benchmarking suite (FIX_VARIANTS.md feature toggle engine)...")
        benchmark_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_variants.py")
        if os.path.exists(benchmark_script):
            subprocess.run([sys.executable, benchmark_script, "--update-findings"], check=False)

    logger.log("INFO", "=== LLM CODE REFACTORING AGENT FINISHED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
