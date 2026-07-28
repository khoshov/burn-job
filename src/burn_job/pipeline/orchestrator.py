"""Autonomous End-to-End Optimization Cycle Orchestrator Module."""

import os
import sys
import json
import subprocess
from typing import Dict, Any

from burn_job.core.config import (
    REPO_ROOT,
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
from burn_job.report.builder import build_findings_from_anomalies, build_schema_report
from burn_job.refinement.iterative_loop import run_iterative_loop

logger = setup_logger("Orchestrator")

class AutonomousOrchestrator:
    """Orchestrates the 8-step end-to-end performance analysis and optimization cycle."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        profile_path: str = DEFAULT_PROFILE_PATH,
        host: str = DEFAULT_HOST,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        offline: bool = True,
        log_path: str = RUN_LOG_PATH,
        model_path: str = None,
    ):
        self.db_path = db_path
        self.profile_path = profile_path
        self.host = host
        self.max_iterations = max_iterations
        self.offline = offline
        self.log_path = log_path
        self.model_path = model_path
        self.graph_store = KuzuGraphStore(db_path)
        from burn_job.refinement.agent import LLMAgent
        self.agent = LLMAgent(model_path=model_path) if not offline or model_path else None

    def run(self) -> Dict[str, Any]:
        logger.info("==================================================================")
        logger.info(" STARTING AUTONOMOUS PERFORMANCE OPTIMIZATION CYCLE")
        logger.info("==================================================================")

        # STEP 1: Scan REST Controllers
        logger.info("STEP 1/8: Scanning Java REST Controllers...")
        src_dir = os.path.join(REPO_ROOT, "java", "src", "main", "java")
        endpoints = ControllerScanner.scan_directory(src_dir)
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
        findings_json_path = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")
        report = build_schema_report("sandbox", "hard", findings, checked_not_issue)
        os.makedirs(os.path.dirname(findings_json_path) or ".", exist_ok=True)
        with open(findings_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Exported {len(findings)} findings to {findings_json_path}")

        # STEP 6 & 7: LLM Refactoring Self-Optimization Loop
        logger.info("STEP 6-7/8: Running LLM self-optimization loop...")
        modified_files = 0
        for finding in findings:
            rel_file = finding.get("file")
            if not rel_file:
                continue
            abs_file = os.path.join(REPO_ROOT, rel_file)
            if not os.path.exists(abs_file):
                continue

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

        # STEP 8: Final Verification & Selection
        logger.info("STEP 8/8: Verifying Maven build...")
        java_dir = os.path.join(REPO_ROOT, "java")
        mvn_res = subprocess.run(["mvn", "test-compile", "-q"], cwd=java_dir, capture_output=True, text=True)
        build_success = (mvn_res.returncode == 0)

        logger.info("==================================================================")
        logger.info(f" AUTONOMOUS OPTIMIZATION CYCLE COMPLETE!")
        logger.info(f"    - Endpoints Profiled: {len(endpoints)}")
        logger.info(f"    - Findings Detected:  {len(findings)}")
        logger.info(f"    - Files Optimized:    {modified_files}")
        logger.info(f"    - Maven Build Status: {'PASSED' if build_success else 'FAILED'}")
        logger.info("==================================================================")

        return {
            "success": build_success,
            "endpoints_count": len(endpoints),
            "findings_count": len(findings),
            "modified_files": modified_files,
            "build_success": build_success,
        }
