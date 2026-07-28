#!/usr/bin/env python3
"""
T5. Избыточные проверки и блоки кода (Redundant Checks & Dead Code)
Detects uncalled / unreachable methods across profiling runs and repeated multi-layer validation calls.
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


def analyze_t5(conn) -> list:
    anomalies = []

    # 1. Uncalled / Dead Application Methods (0 samples across runs)
    query_dead_methods = """
        MATCH (m:Method)
        WHERE m.className STARTS WITH 'com.example' AND m.sampleCount = 0
        RETURN m.className + '.' + m.methodName AS method, m.sampleCount
        LIMIT 20
    """
    res = conn.execute(query_dead_methods)
    while res.has_next():
        method, count = res.get_next()
        anomalies.append({
            "taxonomy_id": "T5",
            "category": "REDUNDANT_CHECKS",
            "type": "DEAD_OR_UNREACHABLE_CODE",
            "severity": "LOW",
            "caller": "Application Stack",
            "callee": method,
            "sample_count": 0,
            "percentage": 0.0,
            "description": f"Method '{method}' has 0 samples across profiling runs. Potential dead code or unexecuted branch."
        })

    # 2. Duplicate Validation Checks across Call Stack Layers
    query_duplicate_validation = """
        MATCH (a:Method)-[r1:CALLS]->(b:Method)-[r2:CALLS]->(c:Method)
        WHERE (a.methodName CONTAINS 'validate' OR a.methodName CONTAINS 'check')
          AND (c.methodName CONTAINS 'validate' OR c.methodName CONTAINS 'check')
        RETURN a.className + '.' + a.methodName AS caller, c.className + '.' + c.methodName AS callee, r1.count AS count
        ORDER BY r1.count DESC
    """
    res = conn.execute(query_duplicate_validation)
    while res.has_next():
        caller, callee, count = res.get_next()
        if count > 5:
            anomalies.append({
                "taxonomy_id": "T5",
                "category": "REDUNDANT_CHECKS",
                "type": "DUPLICATE_LAYER_VALIDATION",
                "severity": "MEDIUM",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Redundant validation logic executed both in '{caller}' and deeper in '{callee}'. Consolidate validation into single layer."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T5 Analyzer: Redundant checks and dead code")
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
    results = analyze_t5(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T5. REDUNDANT CHECKS & DEAD CODE REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
