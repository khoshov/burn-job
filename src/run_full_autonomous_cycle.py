#!/usr/bin/env python3
"""
Complete End-to-End Autonomous Optimization Cycle Orchestrator Wrapper.
Forwards to core.orchestrator.
"""

import sys
import os
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.orchestrator import AutonomousOrchestrator


def run_full_cycle(
    db_path: str = None,
    profile_path: str = None,
    max_iterations: int = 3,
    host: str = "http://localhost:8080",
    offline: bool = True,
    run_log_path: str = None,
) -> dict:
    orchestrator = AutonomousOrchestrator(
        db_path=db_path or os.path.join(REPO_ROOT, "test_pipeline.db"),
        profile_path=profile_path or os.path.join(REPO_ROOT, "profiling_full_taxonomy.collapsed"),
        host=host,
        max_iterations=max_iterations,
        offline=offline,
        log_path=run_log_path or os.path.join(REPO_ROOT, "runlog", "agent_run.log"),
    )
    return orchestrator.run()


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
