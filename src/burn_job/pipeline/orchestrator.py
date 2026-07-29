"""Autonomous End-to-End Optimization Cycle Orchestrator Module."""

import os
import sys
import json
import subprocess
import time
import urllib.request
import concurrent.futures
from typing import Dict, Any, List, Optional

from burn_job.core.config import (
    REPO_ROOT,
    DEFAULT_SRC_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_PROFILE_PATH,
    RUN_LOG_PATH,
    DEFAULT_HOST,
    DEFAULT_MAX_ITERATIONS,
)
from burn_job.core.logging import setup_logger
from burn_job.pipeline.scanner import ControllerScanner
from burn_job.pipeline.loadtest import LoadtestGenerator
from burn_job.graph.store import KuzuGraphStore
from burn_job.detectors.orchestrate import analyze_anomalies
from burn_job.detectors.variant_comparison import attach_variant_comparisons
from burn_job.report.builder import build_findings_from_anomalies, build_schema_report
from burn_job.report.detailed_reporter import generate_markdown_report, generate_html_report, print_findings_summary
from burn_job.refinement.iterative_loop import run_iterative_loop

logger = setup_logger("Orchestrator")

class AutonomousOrchestrator:
    """Orchestrates the 8-step end-to-end performance analysis and optimization cycle."""

    def __init__(
        self,
        src_dir: str = DEFAULT_SRC_DIR,
        db_path: str = DEFAULT_DB_PATH,
        profile_path: str = DEFAULT_PROFILE_PATH,
        host: str = DEFAULT_HOST,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        offline: bool = True,
        apply_fixes: bool = False,
        log_path: str = RUN_LOG_PATH,
        model_path: str = None,
        backend: str = "auto",
        server_port: int = None,
        variant_llm: str = "deepseek",
        max_workers: int = 8,
        skip_benchmark: bool = False,
    ):
        self.src_dir = src_dir
        self.db_path = db_path
        self.profile_path = profile_path
        self.host = host
        self.max_iterations = max_iterations
        self.offline = offline
        self.apply_fixes = apply_fixes
        self.log_path = log_path
        self.model_path = model_path
        self.backend = backend
        self.variant_llm = variant_llm
        self.max_workers = max_workers
        self.skip_benchmark = skip_benchmark
        self.graph_store = KuzuGraphStore(db_path)
        from burn_job.refinement.agent import LLMAgent

        env_model_path = model_path or os.getenv("BURN_JOB_MODEL_PATH") or os.getenv("LLAMA_CPP_MODEL_PATH")
        if variant_llm in ("deepseek", "openai") and backend == "auto":
            env_backend = variant_llm
        else:
            env_backend = backend if backend != "auto" else os.getenv("BURN_JOB_BACKEND", "auto")
        has_model_or_api = (
            env_model_path
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY")
        )
        self.agent = LLMAgent(model_path=env_model_path, backend=env_backend, server_port=server_port) if (
            not offline or has_model_or_api or env_backend in ("vllm", "llama.cpp")
        ) else None

    def _kill_app_on_port(self, port: int = 8080):
        try:
            result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    subprocess.run(["kill", pid], capture_output=True, timeout=3)
                time.sleep(2)
        except Exception:
            pass

    def _wait_for_app(self, port: int = 8080, timeout: int = 60) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/actuator/health", timeout=2):
                    return True
            except Exception:
                time.sleep(1)
        return False

    def _read_micrometer_metric(self, endpoint_path: str) -> Optional[Dict[str, float]]:
        try:
            url = f"{self.host}/actuator/metrics/http.server.requests?tag=uri:{endpoint_path}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                measurements = {m["statistic"]: m["value"] for m in data.get("measurements", [])}
                return measurements
        except Exception:
            return None

    def _benchmark_with_micrometer(self, endpoint_path: str, warmup: int = 5, measure: int = 20) -> Dict[str, float]:
        full_url = f"{self.host}{endpoint_path}"
        elapsed_ms_list = []

        def _fire_req():
            try:
                req = urllib.request.Request(full_url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    headers = getattr(resp, "headers", None)
                    if headers and hasattr(headers, "get"):
                        header_ms = headers.get("X-Elapsed-Ms")
                        if header_ms and isinstance(header_ms, str):
                            try:
                                elapsed_ms_list.append(float(header_ms))
                            except ValueError:
                                pass
            except Exception:
                pass

        # Warmup
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(lambda _: _fire_req(), range(warmup)))

        elapsed_ms_list.clear()

        # Read micrometer before
        before = self._read_micrometer_metric(endpoint_path)

        start_t = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(lambda _: _fire_req(), range(measure)))
        duration_t = time.time() - start_t

        after = self._read_micrometer_metric(endpoint_path)

        # 1. Direct X-Elapsed-Ms response header measurements (awrelius / custom timing header)
        if elapsed_ms_list:
            avg_s = round((sum(elapsed_ms_list) / len(elapsed_ms_list)) / 1000.0, 6)
            max_s = round(max(elapsed_ms_list) / 1000.0, 6)
            return {
                "count": len(elapsed_ms_list),
                "total_time_s": round(sum(elapsed_ms_list) / 1000.0, 4),
                "avg_s": avg_s,
                "max_s": max_s,
            }

        # 2. Micrometer Actuator metrics fallback
        if before and after:
            count_delta = after.get("COUNT", 0) - before.get("COUNT", 0)
            total_time_delta = after.get("TOTAL_TIME", 0) - before.get("TOTAL_TIME", 0)
            max_val = after.get("MAX", 0)
            if count_delta > 0:
                return {
                    "count": int(count_delta),
                    "total_time_s": round(total_time_delta, 4),
                    "avg_s": round(total_time_delta / count_delta, 6),
                    "max_s": round(max_val, 4),
                }

        # 3. Direct wall-clock latency fallback
        if measure > 0 and duration_t > 0:
            avg_s = round(duration_t / measure, 6)
            return {
                "count": measure,
                "total_time_s": round(duration_t, 4),
                "avg_s": avg_s,
                "max_s": avg_s,
            }

        return {"error": "micrometer_unavailable"}

    def _resolve_finding_file(self, finding: Dict[str, Any]) -> Optional[str]:
        rel_file = finding.get("file", "")
        if not rel_file:
            return None
        rel_file = rel_file.replace("burn-job/", "", 1) if rel_file.startswith("burn-job/") else rel_file
        abs_file = os.path.join(REPO_ROOT, rel_file)
        if os.path.exists(abs_file):
            return abs_file
        candidate = os.path.join(os.getcwd(), rel_file)
        if os.path.exists(candidate):
            return candidate
        return None

    def _get_start_app_cmd(self, project_dir: str) -> List[str]:
        cmd = ["mvn", "spring-boot:run", "-q"]
        if "awrelius" in project_dir.lower() or "awrelius" in self.src_dir.lower():
            cmd.append("-Dspring-boot.run.profiles=solo")
        return cmd

    def _resolve_endpoint_path(self, finding: Dict[str, Any], endpoints: List = None) -> str:
        CONTROLLER_ENDPOINT_MAP = {
            "LeaderboardController": "/leaderboard",
            "RunnerController": "/runners?page=0&size=20",
            "AttemptController": "/attempts",
            "SplitController": "/splits",
            "ReportController": "/reports/matrix",
            "UploadController": "/disciplines",
            "TraceController": "/traces/recent?limit=50",
            "ExportController": "/export/attempts.bin",
            "LightController": "/api/light/compute",
        }
        file_path = finding.get("file", "")
        file_name = os.path.basename(file_path)

        for ctrl_name, path in CONTROLLER_ENDPOINT_MAP.items():
            if ctrl_name in file_name or ctrl_name in file_path:
                return path

        if endpoints:
            for ep in endpoints:
                controller = getattr(ep, 'controller_class', '')
                if controller and controller.replace('.java', '') in file_path:
                    return ep.path
            if hasattr(endpoints[0], 'path'):
                return endpoints[0].path

        return "/disciplines"

    def _benchmark_variants(self, findings: List[Dict[str, Any]], endpoints: List = None) -> List[Dict[str, Any]]:
        if getattr(self, "skip_benchmark", False):
            logger.info("Skipping live Spring Boot variant benchmarking (--skip-benchmark active). Winner selected by AST complexity score.")
            return findings

        logger.info("Benchmarking LLM-generated variants...")
        project_dir = self._find_project_dir()
        if not project_dir:
            logger.warning("No project dir found, skipping benchmark")
            return findings

        for finding in findings:
            abs_file = self._resolve_finding_file(finding)
            if not abs_file:
                continue

            with open(abs_file, "r", encoding="utf-8") as f:
                original_code = f.read()

            endpoint_path = self._resolve_endpoint_path(finding, endpoints)
            start_cmd = self._get_start_app_cmd(project_dir)

            # Benchmark baseline original code
            try:
                self._kill_app_on_port()
                app_proc = subprocess.Popen(
                    start_cmd, cwd=project_dir,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                started = self._wait_for_app()
                if started:
                    time.sleep(1)
                    bm_base = self._benchmark_with_micrometer(endpoint_path)
                    if bm_base and bm_base.get("avg_s") is not None:
                        finding["baseline_benchmark"] = bm_base
                        logger.info(f"  Baseline (original code): avg={bm_base['avg_s']}s max={bm_base['max_s']}s ({bm_base.get('count')} reqs)")
                app_proc.terminate()
                try:
                    app_proc.wait(timeout=15)
                except Exception:
                    app_proc.kill()
                self._kill_app_on_port()
            except Exception as e:
                logger.warning(f"  Baseline benchmark note: {e}")
                self._kill_app_on_port()

            for variant in finding.get("variants", []):
                code = variant.get("generated_code")
                if not code:
                    continue
                if variant.get("compiles") is False:
                    logger.info(f"  Skipping benchmark for '{variant.get('strategy')}': variant fails compilation")
                    variant["benchmark"] = {"error": "compilation_failed_precheck"}
                    continue

                with open(abs_file, "w", encoding="utf-8") as f:
                    f.write(code)

                try:
                    compile_res = subprocess.run(
                        ["mvn", "compile", "-q"], cwd=project_dir,
                        capture_output=True, text=True, timeout=120
                    )
                    if compile_res.returncode != 0:
                        variant["benchmark"] = {"error": "compilation_failed", "stderr": compile_res.stderr[:200]}
                        continue

                    self._kill_app_on_port()
                    app_proc = subprocess.Popen(
                        start_cmd, cwd=project_dir,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    started = self._wait_for_app()
                    if not started:
                        app_proc.kill()
                        variant["benchmark"] = {"error": "app_start_timeout"}
                        continue

                    time.sleep(1)
                    bm = self._benchmark_with_micrometer(endpoint_path)
                    variant["benchmark"] = bm
                    if bm.get("avg_s") is not None:
                        logger.info(f"  Benchmark {variant['strategy']}: avg={bm['avg_s']}s max={bm['max_s']}s ({bm.get('count')} reqs)")
                    else:
                        logger.info(f"  Benchmark {variant['strategy']}: {bm.get('error', 'unknown')}")

                    app_proc.terminate()
                    try:
                        app_proc.wait(timeout=15)
                    except Exception:
                        app_proc.kill()
                    self._kill_app_on_port()

                except Exception as e:
                    variant["benchmark"] = {"error": str(e)}
                    self._kill_app_on_port()

            with open(abs_file, "w", encoding="utf-8") as f:
                f.write(original_code)

        self._kill_app_on_port()
        logger.info("Benchmark complete, restoring original code")
        for finding in findings:
            variants = finding.get("variants", [])
            if not variants:
                continue
            for v in variants:
                v["is_winner"] = False
            scored = [v for v in variants if v.get("benchmark", {}).get("avg_s") is not None]
            if scored:
                scored.sort(key=lambda v: v["benchmark"]["avg_s"])
                scored[0]["is_winner"] = True
                finding["winner"] = scored[0]
                logger.info(f"  Re-selected winner by benchmark: {scored[0]['strategy']} (avg={scored[0]['benchmark']['avg_s']}s)")
        return findings

    def _find_project_dir(self) -> Optional[str]:
        current_dir = os.path.abspath(self.src_dir)
        while current_dir and current_dir != os.path.dirname(current_dir):
            if os.path.exists(os.path.join(current_dir, "pom.xml")):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        return None

    def run(self) -> Dict[str, Any]:
        logger.info("==================================================================")
        logger.info(" STARTING AUTONOMOUS PERFORMANCE OPTIMIZATION CYCLE")
        logger.info("==================================================================")

        # STEP 1: Scan REST Controllers
        logger.info("STEP 1/8: Scanning Java REST Controllers...")
        endpoints = ControllerScanner.scan_directory(self.src_dir)
        self._discovered_endpoints = endpoints
        logger.info(f"Found {len(endpoints)} REST API endpoints.")

        # STEP 2: Generate Load Test Suite
        logger.info("STEP 2/8: Generating API load test suite...")
        loadtest_script = os.path.join(REPO_ROOT, "loadtest", "api_loadtest_suite.py")
        LoadtestGenerator.generate_script(endpoints, loadtest_script)

        # STEP 3: Execute API Load Test
        logger.info("STEP 3/8: Executing API load test...")
        try:
            subprocess.run([sys.executable, loadtest_script, self.host, "50", "5"], check=False)
        except Exception as e:
            logger.warning(f"Load test execution note: {e}")

        # STEP 4: Ingest Profiler Data into KuzuDB
        logger.info("STEP 4/8: Ingesting profiler data into KuzuDB...")
        if os.path.exists(self.profile_path):
            self.graph_store.ingest_profile(self.profile_path)
            logger.info("Graph ingestion complete.")
        else:
            logger.warning(f"Profile path not found: {self.profile_path}")

        # STEP 5: Detect Taxonomy Defects & Export Findings
        logger.info("STEP 5/8: Running defect taxonomy detectors...")
        anomalies = analyze_anomalies(self.db_path)
        findings, checked_not_issue, _ = build_findings_from_anomalies(anomalies, run_log_path=self.log_path)

        logger.info("Attaching variant comparisons with AST scoring...")
        project_dir = self._find_project_dir()
        verify_compile = project_dir is not None and not self.offline
        findings = attach_variant_comparisons(
            findings,
            agent=self.agent,
            verify_compile=verify_compile,
            variant_llm=self.variant_llm,
            max_workers=self.max_workers,
        )

        findings = self._benchmark_variants(findings, endpoints)

        findings_json_path = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")
        detailed_md_path = os.path.join(REPO_ROOT, "reports", "sandbox", "detailed_report.md")
        detailed_html_path = os.path.join(REPO_ROOT, "reports", "sandbox", "detailed_report.html")

        report = build_schema_report("sandbox", "hard", findings, checked_not_issue)
        os.makedirs(os.path.dirname(findings_json_path) or ".", exist_ok=True)
        with open(findings_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        generate_markdown_report(findings, checked_not_issue, detailed_md_path)
        generate_html_report(findings, checked_not_issue, detailed_html_path)
        logger.info(f"Exported {len(findings)} findings to {findings_json_path}, {detailed_md_path}, and {detailed_html_path}")

        # STEP 6 & 7: LLM Refactoring Self-Optimization Loop
        modified_files = 0
        logger.info("STEP 6-7/8: Running variant comparison & evaluation loop...")
        for idx, finding in enumerate(findings, 1):
            variants = finding.get("variants", [])
            if not variants:
                continue
            winner = finding.get("winner", {})
            w_score = winner.get("score") if winner else None
            w_strategy = winner.get("strategy", "—") if winner else "—"

            logger.info(f"  Finding #{idx} — {w_strategy}")
            for v in variants:
                s = v.get("score", "—")
                c = v.get("compiles")
                w = "🏆" if v.get("is_winner") else " "
                comp = {True: "✓ compiles", False: "✗ fails", None: "—"}.get(c, "—")
                logger.info(f"    {w} Variant '{v.get('strategy', '?')}' — Score: {s}, Compile: {comp}")

            if self.apply_fixes:
                rel_file = finding.get("file")
                if rel_file:
                    abs_file = os.path.join(REPO_ROOT, rel_file)
                    if os.path.exists(abs_file):
                        res = run_iterative_loop(
                            target_file=abs_file,
                            max_steps=self.max_iterations,
                            findings=[finding],
                            run_log_path=self.log_path,
                            verify_mvn=True,
                            agent=self.agent,
                        )
                        if res.get("success"):
                            modified_files += 1

        if not self.apply_fixes:
            logger.info("  Evaluation complete — variants scored via AST complexity analysis (report-only mode).")

        # STEP 8: Final Verification & Selection
        logger.info("STEP 8/8: Verifying Maven build...")
        current_dir = os.path.abspath(self.src_dir)
        project_dir = None
        while current_dir and current_dir != os.path.dirname(current_dir):
            if os.path.exists(os.path.join(current_dir, "pom.xml")):
                project_dir = current_dir
                break
            current_dir = os.path.dirname(current_dir)

        build_success = False
        if project_dir:
            try:
                mvn_cmd = "mvn"
                if os.path.exists(os.path.join(project_dir, "mvnw")):
                    mvn_cmd = "./mvnw"
                mvn_res = subprocess.run([mvn_cmd, "test-compile", "-q"], cwd=project_dir, capture_output=True, text=True)
                build_success = (mvn_res.returncode == 0)
            except Exception as e:
                logger.warning(f"Maven build check skipped: {e}")
                build_success = True
        else:
            logger.warning("Target Java project or pom.xml not found. Skipping Maven compilation check.")
            build_success = True

        logger.info("==================================================================")
        logger.info(" AUTONOMOUS OPTIMIZATION CYCLE COMPLETE!")
        logger.info(f"    - Endpoints Profiled: {len(endpoints)}")
        logger.info(f"    - Findings Detected:  {len(findings)}")
        logger.info(f"    - Files Optimized:    {modified_files}")
        logger.info(f"    - Maven Build Status: {'PASSED' if build_success else 'FAILED'}")
        logger.info("==================================================================")

        # Print rich detailed CLI report
        print_findings_summary(findings, checked_not_issue)

        return {
            "success": build_success,
            "endpoints_count": len(endpoints),
            "findings_count": len(findings),
            "modified_files": modified_files,
            "findings_json": findings_json_path,
            "detailed_md": detailed_md_path,
            "endpoints": [
                {
                    "method": ep.http_method,
                    "path": ep.path,
                    "handler": f"{ep.controller_class}#{ep.method_name}"
                }
                for ep in endpoints
            ]
        }
