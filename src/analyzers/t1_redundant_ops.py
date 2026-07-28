#!/usr/bin/env python3
"""
T1. Избыточные вычисления и операции (Redundant Computations & Operations)
Detects unbatched loop saves and excessive string concatenation in loops.

Both rules now live in rules/graph_rules.yaml (spec 010) — SAVE_IN_LOOP_UNBATCHED's primary home
moved to T6 (it was previously duplicated verbatim in both t1_redundant_ops.py and t6_db_queries.py;
see plan/010's Problem section), tagged also_relevant_to: [T1] there. EXCESSIVE_STRING_CONCAT stays
primary here. See static_pattern_detectors.detect_duplicate_methods (spec 009) for the newer,
structural (non name-based) T1 duplicate-code detector.
"""

import sys
import os
import argparse
import json

_SCRIPTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False

import rule_engine  # noqa: E402


def analyze_t1(conn) -> list:
    return rule_engine.run(conn, "T1")


def main():
    parser = argparse.ArgumentParser(description="T1 Analyzer: Redundant computations and operations")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder")
    parser.add_argument("--json", action="store_true", help="Output findings as JSON")
    args = parser.parse_args()

    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(args.db_path):
        print(f"Error: KùzuDB database path '{args.db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)
    results = analyze_t1(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T1. REDUNDANT OPERATIONS REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
