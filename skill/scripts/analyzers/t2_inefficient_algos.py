#!/usr/bin/env python3
"""
T2. Неэффективные алгоритмы (Inefficient Algorithms)
Detects quadratic complexity patterns, linear collection searches in hot loops (List.contains / indexOf / remove),
and O(N^2) algorithmic growth.
"""

import sys
import os
import argparse
import json

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def analyze_t2(conn) -> list:
    anomalies = []

    # 1. Linear collection lookups (List.contains, List.indexOf, List.remove) in hot loops
    query_linear_in_loop = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE (b.className CONTAINS 'List' OR b.className CONTAINS 'ArrayList' OR b.className CONTAINS 'LinkedList')
          AND (b.methodName = 'contains' OR b.methodName = 'indexOf' OR b.methodName = 'remove' OR b.methodName = 'containsAll')
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_linear_in_loop)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 20:
            anomalies.append({
                "taxonomy_id": "T2",
                "category": "INEFFICIENT_ALGORITHMS",
                "type": "LINEAR_SEARCH_IN_LOOP",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' performs linear search O(N) via '{callee}' in hot loops ({count} samples). Risk of quadratic complexity O(N^2). Consider HashSet / HashMap."
            })

    # 2. Check for nested loop quadratic operations
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
