#!/usr/bin/env python3
"""
Complete End-to-End Autonomous Optimization Cycle Orchestrator.

Implements the full 8-step pipeline:
  1. Scan Java Spring Controllers (src/main/java)
  2. Generate & run API load tests (light load)
  3. Capture Micrometer metrics (/actuator/metrics/http.server.requests)
  4. Ingest JFR / profile data under API load into KùzuDB
  5. Detect taxonomy anomalies (T1-T9) & filter Section 7 non-defects -> findings.json
  6. Launch LLM Agent in iterative self-optimization mode (Generator -> Verifier -> Evaluator)
  7. Re-run API tests & JFR profiling across candidate iterations
  8. Select best candidate and apply verified fixes to code + write audit log
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from generate_api_loadtests import scan_spring_controllers, generate_loadtest_script, fetch_micrometer_metrics, generate_report
from jfr_to_graph import parse_profile, ingest_to_kuzu
from analyze_anomalies import analyze_anomalies
from export_report import build_findings_from_anomalies, build_schema_report
from iterative_agent_loop import run_iterative_loop


def _log(msg: str):
    timestamp = datetime.datetime.now().isoformat()
    line = f"[{timestamp}] [AutonomousCycle] {msg}"
    print(line, flush=True)


def run_full_cycle(
    db_path: str = None,
    profile_path: str = None,
    max_iterations: int = 3,
    host: str = "http://localhost:8080",
    offline: bool = True,
    run_log_path: str = None,
) -> dict:
    if not db_path:
        db_path = os.path.join(REPO_ROOT, "test_pipeline.db")
    if not profile_path:
        profile_path = os.path.join(REPO_ROOT, "profiling_full_taxonomy.collapsed")
    if not run_log_path:
        run_log_path = os.path.join(REPO_ROOT, "runlog", "agent_run.log")

    print("\n" + "=" * 70)
    print(" 🚀 STARTING FULL AUTONOMOUS PERFORMANCE OPTIMIZATION CYCLE")
    print("=" * 70 + "\n")

    # STEP 1: Scan Java Controllers
    _log("STEP 1/8: Scanning Java REST Controllers in src/main/java...")
    src_dir = os.path.join(REPO_ROOT, "src", "main", "java")
    endpoints = scan_spring_controllers(src_dir)
    _log(f"Found {len(endpoints)} REST API endpoints.")

    # STEP 2: Generate & Run API Load Test
    _log("STEP 2/8: Generating API load test suite...")
    out_script = os.path.join(REPO_ROOT, "loadtest", "api_loadtest_suite.py")
    generate_loadtest_script(endpoints, out_script)

    _log("STEP 3/8: Measuring baseline Micrometer metrics & executing API load test...")
    before_metrics = fetch_micrometer_metrics(host)
    start_time = time.time()
    try:
        subprocess.run([sys.executable, out_script, host, "50", "5"], check=False)
    except Exception as e:
        _log(f"Load test execution note: {e}")
    duration_sec = time.time() - start_time
    after_metrics = fetch_micrometer_metrics(host)

    md_report = os.path.join(REPO_ROOT, "reports", "sandbox", "micrometer_api_report.md")
    json_report = os.path.join(REPO_ROOT, "reports", "sandbox", "micrometer_api_results.json")
    generate_report(endpoints, before_metrics, after_metrics, duration_sec, md_report, json_report)
    _log("Micrometer API report generated.")

    # STEP 4: Ingest JFR / Profile into KùzuDB
    _log("STEP 4/8: Ingesting JFR/collapsed profiling data into KùzuDB graph database...")
    edge_counts, method_counts, total_samples, other_jfr_events = parse_profile(profile_path)
    ingest_to_kuzu(db_path, run_id="baseline_run", test_name="api_loadtest", edge_counts=edge_counts, method_counts=method_counts, total_samples=total_samples, other_jfr_events=other_jfr_events)
    _log(f"KùzuDB graph built with {len(method_counts)} methods ({total_samples} samples).")

    # STEP 5: Detect Anomalies & Export findings.json
    _log("STEP 5/8: Running T1-T9 taxonomy analyzers & Section 7 non-defect rules...")
    anomalies = analyze_anomalies(db_path)
    findings, checked_not_issue, skipped = build_findings_from_anomalies(anomalies, run_log_path=run_log_path)

    findings_json_path = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")
    report = build_schema_report("sandbox", "hard", findings, checked_not_issue)
    os.makedirs(os.path.dirname(findings_json_path) or ".", exist_ok=True)
    with open(findings_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    _log(f"Exported {len(findings)} findings to {findings_json_path}")

    # STEP 6 & 7: Run LLM Agent Iterative Self-Optimization Loop
    _log(f"STEP 6-7/8: Launching LLM Agent iterative loop (max_iterations={max_iterations})...")
    modified_files = 0
    for finding in findings:
        rel_file = finding.get("file")
        if not rel_file:
            continue
        abs_file = os.path.join(REPO_ROOT, rel_file)
        if not os.path.exists(abs_file):
            continue

        _log(f"Optimizing bottleneck file: {rel_file}...")
        res = run_iterative_loop(
            target_file=abs_file,
            max_steps=max_iterations,
            findings=[finding],
            offline=offline,
            run_log_path=run_log_path,
            verify_mvn=True,
        )
        if res.get("success"):
            modified_files += 1

    # STEP 8: Selection & Final Verification
    _log("STEP 8/8: Verifying final Maven build & selecting best candidates...")
    mvn_res = subprocess.run(["mvn", "test-compile", "-q"], cwd=REPO_ROOT, capture_output=True, text=True)
    build_success = (mvn_res.returncode == 0)

    print("\n" + "=" * 70)
    print(" 🎉 AUTONOMOUS OPTIMIZATION CYCLE COMPLETE!")
    print(f"    - Endpoints Profiled: {len(endpoints)}")
    print(f"    - Findings Detected:  {len(findings)}")
    print(f"    - Files Optimized:    {modified_files}")
    print(f"    - Maven Build Status: {'✅ PASSED' if build_success else '❌ FAILED'}")
    print("=" * 70 + "\n")

    return {
        "success": build_success,
        "endpoints_count": len(endpoints),
        "findings_count": len(findings),
        "modified_files": modified_files,
        "build_success": build_success,
    }


def main():
    parser = argparse.ArgumentParser(description="Full End-to-End Autonomous Optimization Cycle")
    parser.add_argument("--db-path", help="Path to KùzuDB database")
    parser.add_argument("--profile", help="Path to JFR/collapsed profile file")
    parser.add_argument("--max-steps", type=int, default=3, help="Max iterations for self-optimization loop")
    parser.add_argument("--host", default="http://localhost:8080", help="Target API host")
    parser.add_argument("--online", action="store_true", help="Enable online LLM API calls instead of offline engine")
    args = parser.parse_args()

    run_full_cycle(
        db_path=args.db_path,
        profile_path=args.profile,
        max_iterations=args.max_steps,
        host=args.host,
        offline=not args.online,
    )


if __name__ == "__main__":
    main()
