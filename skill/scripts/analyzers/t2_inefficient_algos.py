#!/usr/bin/env python3
"""
T2. Неэффективные алгоритмы (Inefficient Algorithms)
Detects quadratic complexity patterns, linear collection searches in hot loops (List.contains /
indexOf / remove), and O(N^2) algorithmic growth.

LINEAR_SEARCH_IN_LOOP now lives in rules/graph_rules.yaml (spec 010). QUADRATIC_NESTED_LOOP stays
custom Python here — it's a 2-edge chain match (a->b->c), which doesn't fit the engine's
single-edge/single-node schema (see rule_engine.py's module docstring). See
static_pattern_detectors.detect_nested_loops (spec 009) for the newer, structural (general
nested-loop-shape, not List.contains-specific) detector.
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


def analyze_t2(conn) -> list:
    anomalies = rule_engine.run(conn, "T2")

    # Nested loop quadratic operations — a 2-edge chain, not migrated (see module docstring).
    query_nested_loop = """
        MATCH (a:Method)-[r1:CALLS]->(b:Method)-[r2:CALLS]->(c:Method)
        WHERE b.methodName CONTAINS 'forEach' OR b.methodName CONTAINS 'map' OR b.methodName CONTAINS 'iterator'
          AND (c.className CONTAINS 'List' AND c.methodName = 'contains')
        RETURN a.className + '.' + a.methodName AS caller, c.className + '.' + c.methodName AS callee, r1.count + r2.count AS total_count
        ORDER BY total_count DESC
    """
    res = conn.execute(query_nested_loop)
    while res.has_next():
        caller, callee, count = res.get_next()
        if count > 30:
            anomalies.append({
                "taxonomy_id": "T2",
                "category": "INEFFICIENT_ALGORITHMS",
                "type": "QUADRATIC_NESTED_LOOP",
                "severity": "CRITICAL",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Nested loop iteration in '{caller}' invokes O(N) lookup '{callee}'. Total complexity is O(N^2)."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T2 Analyzer: Inefficient algorithms")
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
    results = analyze_t2(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T2. INEFFICIENT ALGORITHMS REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
