#!/usr/bin/env python3
"""
T1. Избыточные вычисления и операции (Redundant Computations & Operations)
Detects unbatched loop saves, repeated operations, and excessive string concatenation in loops.
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


def analyze_t1(conn) -> list:
    anomalies = []

    # 1. Unbatched persistence in loops (Save in Loop)
    query_save_in_loop = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.methodName CONTAINS 'performSave' OR b.methodName CONTAINS 'save' OR b.className CONTAINS 'AbstractSaveEventListener'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_save_in_loop)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T1",
                "category": "REDUNDANT_OPERATIONS",
                "type": "SAVE_IN_LOOP_UNBATCHED",
                "severity": "CRITICAL",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' invokes entity persistence inside loops ({count} samples). Unbatched repeated work causes N DB network roundtrips."
            })

    # 2. Excessive string allocation & concatenation in loops
    query_string_concat = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'StringBuilder' OR (b.className CONTAINS 'String' AND b.methodName CONTAINS 'concat')
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_string_concat)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T1",
                "category": "REDUNDANT_OPERATIONS",
                "type": "EXCESSIVE_STRING_CONCAT",
                "severity": "MEDIUM",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' performs redundant string concatenation inside loops ({count} samples). High allocation overhead."
            })

    return anomalies


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
