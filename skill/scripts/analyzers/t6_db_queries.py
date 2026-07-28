#!/usr/bin/env python3
"""
T6. Ошибки в запросах к базе данных (Database Query Errors)
Detects N+1 query problems, lack of JDBC batching (saves in loops), and connection pool starvation.

All three rules now live in rules/graph_rules.yaml (spec 010). SAVE_IN_LOOP_UNBATCHED's primary
home moved here from t1_redundant_ops.py — it was byte-for-byte duplicated across both files
(see plan/010's Problem section); it's now registered exactly once, tagged also_relevant_to: [T1].
See static_pattern_detectors.detect_n_plus_one (spec 009) for the newer, structural (JPA-annotation
+ loop-shape based, not name-based) N+1 detector.
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


def analyze_t6(conn) -> list:
    return rule_engine.run(conn, "T6")


def main():
    parser = argparse.ArgumentParser(description="T6 Analyzer: Database query errors")
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
    results = analyze_t6(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T6. DATABASE QUERY ERRORS REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
