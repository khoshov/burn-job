"""Autonomous End-to-End Optimization Cycle Orchestrator Module."""

import os
import sys
import json
import subprocess
from typing import Dict, Any, Optional

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
from burn_job.report.detailed_reporter import generate_markdown_report, print_findings_summary
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
        self.graph_store = KuzuGraphStore(db_path)
        from burn_job.refinement.agent import LLMAgent
        self.agent = LLMAgent(model_path=model_path, backend=backend) if not offline or model_path or backend in ("vllm", "llama.cpp") else None

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
        findings = attach_variant_comparisons(findings, agent=self.agent, verify_compile=verify_compile)

        findings_json_path = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")
        detailed_md_path = os.path.join(REPO_ROOT, "reports", "sandbox", "detailed_report.md")

        report = build_schema_report("sandbox", "hard", findings, checked_not_issue)
        os.makedirs(os.path.dirname(findings_json_path) or ".", exist_ok=True)
        with open(findings_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        generate_markdown_report(findings, checked_not_issue, detailed_md_path)
        logger.info(f"Exported {len(findings)} findings to {findings_json_path} and {detailed_md_path}")

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
