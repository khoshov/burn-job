"""
LLM-Based Code Refactoring Agent for Java / Spring Boot Performance Antipatterns.
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

from burn_job.refinement.evaluator import evaluate_variant_candidates, JFRProfiler

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
DEFAULT_LOG_PATH = os.path.join(REPO_ROOT, "runlog", "agent_run.log")

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
Each variant MUST be a COMPLETE, compilable Java source file containing the package declaration, all imports, and the full public class definition.
"""

HAS_MULTI_JFR_EVAL = True


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


def find_default_model_path() -> Optional[str]:
    """Search for existing GGUF model files in the workspace."""
    candidate_dirs = [
        os.path.join(REPO_ROOT, "Qwen3-4B "),
        os.path.join(REPO_ROOT, "Qwen3-4B"),
        os.path.join(REPO_ROOT, "models"),
        REPO_ROOT,
    ]
    for d in candidate_dirs:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".gguf"):
                    return os.path.join(d, f)
    return None


class LLMAgent:
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        model_path: str = None,
        backend: str = None,
        n_ctx: int = 8192,
        n_gpu_layers: int = -1,
        logger: LLMAgentLogger = None,
    ):
        self.logger = logger or LLMAgentLogger()
        self.backend = (backend or os.getenv("BURN_JOB_BACKEND") or "auto").lower()
        self.model_path = (
            model_path
            or os.getenv("BURN_JOB_MODEL_PATH")
            or os.getenv("LLAMA_CPP_MODEL_PATH")
            or os.getenv("VLLM_MODEL_PATH")
            or os.getenv("GGUF_MODEL_PATH")
        )

        self.llama_model = None
        self.vllm_engine = None

        # Check vLLM backend direct load
        if self.backend in ("vllm", "auto") and not self.llama_model:
            vllm_target = self.model_path or (REPO_ROOT if os.path.exists(os.path.join(REPO_ROOT, "Qwen3-4B ", "config.json")) else None)
            if vllm_target or self.backend == "vllm":
                try:
                    from vllm import LLM, SamplingParams
                    target = vllm_target or "Qwen/Qwen2.5-Coder-7B-Instruct"
                    self.logger.log("INFO", f"Initializing local vLLM engine with model/dir: {target}")
                    self.vllm_engine = LLM(model=target, trust_remote_code=True)
                    self.vllm_sampling_params = SamplingParams(temperature=0.2, max_tokens=4096)
                    self.logger.log("SUCCESS", "Local vLLM engine initialized successfully.")
                except ImportError:
                    if self.backend == "vllm":
                        self.logger.log("WARNING", "vllm package not installed. Install via `pip install vllm`.")
                except Exception as e:
                    self.logger.log("ERROR", f"Failed to initialize vLLM engine: {str(e)}")

        # Check llama.cpp backend load
        if self.backend in ("llama.cpp", "auto") and not self.vllm_engine:
            if not self.model_path:
                self.model_path = find_default_model_path()

            if self.model_path and os.path.exists(self.model_path):
                self.logger.log("INFO", f"Initializing local llama.cpp engine with model: {self.model_path}")
                try:
                    from llama_cpp import Llama
                    self.llama_model = Llama(
                        model_path=self.model_path,
                        n_ctx=n_ctx,
                        n_gpu_layers=n_gpu_layers,
                        verbose=False,
                    )
                    self.logger.log("SUCCESS", f"Local llama.cpp engine initialized (model={os.path.basename(self.model_path)}).")
                except ImportError:
                    if self.backend == "llama.cpp":
                        self.logger.log("WARNING", "llama-cpp-python package not found. Install via `pip install llama-cpp-python`.")
                except Exception as e:
                    self.logger.log("ERROR", f"Failed to load llama.cpp model from {self.model_path}: {str(e)}")

        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GIGACHAT_API_KEY") or os.getenv("LLM_API_KEY")
        default_base_url = "https://api.deepseek.com/v1" if (self.api_key and "deepseek" in (base_url or "").lower()) or os.getenv("DEEPSEEK_API_KEY") else "https://api.openai.com/v1"
        self.base_url = (base_url or os.getenv("VLLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or default_base_url).rstrip("/")

        default_model = "qwen3" if (self.llama_model or self.vllm_engine) else ("deepseek-chat" if "deepseek" in self.base_url.lower() else "gpt-4o")
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or default_model

    def is_api_configured(self) -> bool:
        return (self.vllm_engine is not None) or (self.llama_model is not None) or bool(self.api_key)

    def call_llm(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        if self.vllm_engine is not None:
            self.logger.log("INFO", "Executing inference via local python vLLM engine...")
            try:
                full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
                outputs = self.vllm_engine.generate([full_prompt], self.vllm_sampling_params)
                return outputs[0].outputs[0].text
            except Exception as e:
                self.logger.log("ERROR", f"Local vLLM execution error: {str(e)}")
                raise

        if self.llama_model is not None:
            self.logger.log("INFO", "Executing inference via local python llama.cpp (Qwen3)...")
            try:
                response = self.llama_model.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=4096,
                )
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                self.logger.log("ERROR", f"Local llama.cpp execution error: {str(e)}")
                raise

        if not self.is_api_configured():
            raise ValueError("LLM API Key or local model path (llama.cpp/vLLM) not provided. Configure --model-path or --backend vllm.")

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
        candidates = {}
        pattern = r"\[VARIANT_(\d+)\]\s*```java\s*\n(.*?)\n```"
        matches = re.findall(pattern, llm_response, re.DOTALL)
        if matches:
            for idx, code in matches:
                candidates[f"v{idx}"] = code
        else:
            blocks = re.findall(r"```java\s*\n(.*?)\n```", llm_response, re.DOTALL)
            for idx, code in enumerate(blocks, start=1):
                candidates[f"v{idx}"] = code

        if not candidates:
            single = self.extract_code_block(llm_response)
            if single:
                candidates["v1"] = single

        return candidates


    def process_finding(self, finding: dict, root_dir: str, dry_run: bool = False, multi_variant: bool = False, enable_jfr: bool = False) -> bool:
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
            if self.is_api_configured():
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
                    self.logger.log("WARNING", f"LLM Multi-Variant call failed ({e}).")

            if dry_run:
                self.logger.log("INFO", f"[DRY RUN] Generated {len(candidates)} candidate variants for {rel_file}.")
                return True

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
                    self.logger.log("SUCCESS", f"Winning Variant Selected: [{winner_id}] with optimal performance score: {eval_res['best_score']:.2f}")
                else:
                    self.logger.log("WARNING", "No candidate variant passed build/verification. Rolling back to original.")
                    apply_patch(original_code)
                    return False
            else:
                for var_name, code in candidates.items():
                    apply_patch(code)
                    if verify_build():
                        winning_name = var_name
                        winning_code = code
                        break
                if not winning_name:
                    apply_patch(original_code)
                    return False

            apply_patch(winning_code)
            self.logger.log("SUCCESS", f"Applied winning variant [{winning_name}] to {rel_file}.")
            return True

        else:
            new_code = None
            if self.is_api_configured():
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
                    self.logger.log("WARNING", f"LLM call failed ({e}).")

            if dry_run:
                self.logger.log("INFO", f"[DRY RUN] Would write updated content to {rel_file}.")
                return True

            with open(abs_file, "w", encoding="utf-8") as f:
                f.write(new_code)

            self.logger.log("SUCCESS", f"Successfully applied refactoring to {rel_file}.")
            return True

    def verify_maven_build(self, root_dir: str) -> bool:
        self.logger.log("INFO", "Executing Maven verification (mvn test-compile)...")
        java_dir = os.path.join(root_dir, "java") if os.path.exists(os.path.join(root_dir, "java", "pom.xml")) else root_dir
        try:
            res = subprocess.run(["mvn", "test-compile"], cwd=java_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
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
    parser.add_argument("--model", help="LLM model name (e.g. qwen3, deepseek-chat, gpt-4o)")
    parser.add_argument("--model-path", help="Path to local model file/directory for llama.cpp or vLLM")
    parser.add_argument("--backend", choices=["auto", "llama.cpp", "vllm", "openai"], default="auto", help="LLM execution backend (auto, llama.cpp, vllm, openai)")
    parser.add_argument("--n-ctx", type=int, default=8192, help="Context window size for local model")
    parser.add_argument("--n-gpu-layers", type=int, default=-1, help="Number of GPU layers to offload (-1 for all)")
    parser.add_argument("--api-key", help="API key for LLM provider")
    parser.add_argument("--base-url", help="Base URL for OpenAI-compatible LLM endpoint (or vLLM server http://localhost:8000/v1)")
    parser.add_argument("--dry-run", action="store_true", help="Perform analysis without writing changes to disk")
    parser.add_argument("--no-verify", action="store_true", help="Skip Maven compilation verification")
    parser.add_argument("--multi-variant", action="store_true", help="Generate all possible candidate variants for each bottleneck")
    parser.add_argument("--enable-jfr", action="store_true", help="Capture JFR profiles across candidate variants and select winner by performance score")
    parser.add_argument("--benchmark-all-variants", action="store_true", help="Run multi-variant feature toggle benchmarking suite to select winner")
    parser.add_argument("--iterative", action="store_true", help="Enable iterative self-optimization loop")
    parser.add_argument("--max-steps", type=int, default=3, help="Maximum number of self-optimization iterations (default: 3)")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.src_dir)
    logger = LLMAgentLogger()
    logger.log("INFO", "=== STARTING LLM CODE REFACTORING & JFR EVALUATION AGENT ===")

    report_path = args.report
    if not os.path.isabs(report_path):
        report_path = os.path.join(root_dir, report_path)

    if not os.path.exists(report_path):
        from burn_job.report.builder import generate_burn_job_report
        logger.log("INFO", "Report file not found. Generating from report.builder...")
        report_data = generate_burn_job_report()
        findings = report_data["findings"]
    else:
        findings = load_findings(report_path)

    logger.log("INFO", f"Loaded {len(findings)} findings from report.")

    agent = LLMAgent(
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        model_path=args.model_path,
        backend=args.backend,
        n_ctx=args.n_ctx,
        n_gpu_layers=args.n_gpu_layers,
        logger=logger,
    )

    if args.iterative:
        logger.log("INFO", f"Mode: Iterative Self-Optimization Loop Enabled (max_steps={args.max_steps}).")
        from burn_job.refinement.iterative_loop import run_iterative_loop
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
                run_log_path=logger.log_path,
                verify_mvn=not args.no_verify,
                agent=agent,
            )
            if res.get("success"):
                modified_count += 1
        logger.log("INFO", f"Iterative refactoring complete. {modified_count}/{len(findings)} target files optimized.")
        sys.exit(0)

    modified_count = 0

    for finding in findings:
        success = agent.process_finding(
            finding,
            root_dir=root_dir,
            dry_run=args.dry_run,

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
        logger.log("INFO", "Running multi-variant benchmarking suite...")
        benchmark_script = os.path.join(_THIS_DIR, "benchmarks.py")
        if os.path.exists(benchmark_script):
            subprocess.run([sys.executable, benchmark_script, "--update-findings"], check=False)

    logger.log("INFO", "=== LLM CODE REFACTORING AGENT FINISHED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
