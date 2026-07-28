"""Unified CLI Entrypoint for Performance Optimization Pipeline."""

import argparse
import sys
import os
import warnings

from burn_job.core.config import REPO_ROOT, DEFAULT_DB_PATH, DEFAULT_PROFILE_PATH, DEFAULT_HOST
from burn_job.core.logging import setup_logger
from burn_job.pipeline.scanner import ControllerScanner
from burn_job.graph.store import KuzuGraphStore
from burn_job.pipeline.orchestrator import AutonomousOrchestrator

logger = setup_logger("CLI")

def main():
    parser = argparse.ArgumentParser(description="Performance Optimization Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    scan_p = subparsers.add_parser("scan", help="Scan Java Spring controllers for endpoints")
    scan_p.add_argument("--src", default=os.path.join(REPO_ROOT, "java", "src", "main", "java"), help="Path to Java source directory")
    scan_p.add_argument("--target", help="[Deprecated] Alias for --src")

    ingest_p = subparsers.add_parser("ingest", help="Ingest profiler stack traces into KuzuDB")
    ingest_p.add_argument("--profile", default=DEFAULT_PROFILE_PATH, help="Path to profile file")
    ingest_p.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to KuzuDB directory")

    cycle_p = subparsers.add_parser("run-cycle", help="Run full 8-step autonomous optimization cycle")
    cycle_p.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to KuzuDB database")
    cycle_p.add_argument("--profile", default=DEFAULT_PROFILE_PATH, help="Path to profile file")
    cycle_p.add_argument("--host", default=DEFAULT_HOST, help="Target API host")
    cycle_p.add_argument("--online", action="store_true", help="Enable online LLM API calls")
    cycle_p.add_argument("--model-path", help="Path to local GGUF model file for llama.cpp")

    version_p = subparsers.add_parser("version", help="Print CLI version")

    args = parser.parse_args()

    # Handle deprecated --target flag if passed
    if hasattr(args, "target") and args.target:
        warnings.warn("The '--target' flag is deprecated for 'scan'; use '--src' instead.", DeprecationWarning)
        args.src = args.target

    if args.command == "scan":
        endpoints = ControllerScanner.scan_directory(args.src)
        print(f"Scanned {len(endpoints)} endpoints:")
        for ep in endpoints:
            print(f"  [{ep.http_method}] {ep.path} -> {ep.controller_class}#{ep.method_name}")

    elif args.command == "ingest":
        store = KuzuGraphStore(args.db)
        success = store.ingest_profile(args.profile)
        if success:
            print("Profile ingested successfully into KuzuDB.")
        else:
            print("Profile ingestion failed.")

    elif args.command == "run-cycle":
        orchestrator = AutonomousOrchestrator(
            db_path=args.db,
            profile_path=args.profile,
            host=args.host,
            offline=not args.online,
            model_path=args.model_path,
        )
        res = orchestrator.run()
        if res.get("success"):
            print("Autonomous cycle finished successfully.")
        else:
            print("Autonomous cycle finished with warnings.")

    elif args.command == "version":
        print("burn-job CLI version 0.1.0")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
