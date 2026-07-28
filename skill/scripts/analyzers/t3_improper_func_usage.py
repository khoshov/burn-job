#!/usr/bin/env python3
"""
T3. Неправильное использование функций (Improper Function / Entity Usage)
Detects fetching full JPA entities / LOB payloads when only identifiers or DTO projections are
required, and full fetches used only to check existence.

Both rules now live in rules/graph_rules.yaml (spec 010). See
static_pattern_detectors.detect_existence_check_full_fetch (spec 009) for the newer, structural
(dataflow-based, not name-based) detector for the existence-check pattern specifically.
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


def analyze_t3(conn) -> list:
    return rule_engine.run(conn, "T3")


def main():
    parser = argparse.ArgumentParser(description="T3 Analyzer: Improper function usage")
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
    results = analyze_t3(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T3. IMPROPER FUNCTION USAGE REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
