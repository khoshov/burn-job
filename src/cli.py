"""
Unified CLI Entrypoint for Performance Optimization Pipeline.
"""

import argparse
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from config import REPO_ROOT, DEFAULT_DB_PATH, DEFAULT_PROFILE_PATH, DEFAULT_HOST
from core.generator import ControllerScanner
from core.graph_store import KuzuGraphStore
from core.orchestrator import AutonomousOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Performance Optimization Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # Command: scan
    scan_p = subparsers.add_parser("scan", help="Scan Java Spring controllers for endpoints")
    scan_p.add_argument("--src", default=os.path.join(REPO_ROOT, "java", "src", "main", "java"), help="Path to Java source directory")

    # Command: ingest
    ingest_p = subparsers.add_parser("ingest", help="Ingest profiler stack traces into KùzuDB")
    ingest_p.add_argument("--profile", default=DEFAULT_PROFILE_PATH, help="Path to profile file")
    ingest_p.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to KùzuDB directory")

    # Command: run-cycle
    cycle_p = subparsers.add_parser("run-cycle", help="Run full 8-step autonomous optimization cycle")
    cycle_p.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to KùzuDB database")
    cycle_p.add_argument("--profile", default=DEFAULT_PROFILE_PATH, help="Path to profile file")
    cycle_p.add_argument("--host", default=DEFAULT_HOST, help="Target API host")
    cycle_p.add_argument("--online", action="store_true", help="Enable online LLM API calls")

    args = parser.parse_args()

    if args.command == "scan":
        endpoints = ControllerScanner.scan_directory(args.src)
        print(f"Scanned {len(endpoints)} endpoints:")
        for ep in endpoints:
            print(f"  [{ep.http_method}] {ep.path} -> {ep.controller_class}#{ep.method_name}")

    elif args.command == "ingest":
        store = KuzuGraphStore(args.db)
        success = store.ingest_profile(args.profile)
        if success:
            print("✅ Profile ingested successfully into KùzuDB.")
        else:
            print("❌ Profile ingestion failed.")

    elif args.command == "run-cycle":
        orchestrator = AutonomousOrchestrator(
            db_path=args.db,
            profile_path=args.profile,
            host=args.host,
            offline=not args.online,
        )
        res = orchestrator.run()
        if res.get("success"):
            print("🎉 Autonomous cycle finished successfully.")
        else:
            print("⚠️ Autonomous cycle finished with warnings.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
