#!/usr/bin/env python3
"""
T3. Неправильное использование функций (Improper Function / Entity Usage)
Detects fetching full JPA entities / LOB payloads when only identifiers or DTO projections are required.
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


def analyze_t3(conn) -> list:
    anomalies = []

    # 1. Heavy Entity Conversion & LOB AttributeConverters
    query_lob_overhead = """
        MATCH (m:Method)
        WHERE m.className CONTAINS 'AttributeConverter' OR m.className CONTAINS 'Converter'
           OR m.className CONTAINS 'TypeDescriptor' OR m.className CONTAINS 'PersistenceContext'
        RETURN m.className + '.' + m.methodName AS method, m.sampleCount
        ORDER BY m.sampleCount DESC
    """
    res = conn.execute(query_lob_overhead)
    while res.has_next():
        method, count = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T3",
                "category": "IMPROPER_FUNCTION_USAGE",
                "type": "HEAVY_ENTITY_FETCH",
                "severity": "MEDIUM",
                "caller": "ORM Subsystem",
                "callee": method,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Heavy entity payload conversion detected in '{method}' ({count} samples). Full entity loaded into PersistenceContext when DTO/Interface Projection is sufficient."
            })

    # 2. Fetching full collection or entity just for exists / count check
    query_full_fetch_for_check = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE (a.methodName CONTAINS 'exists' OR a.methodName CONTAINS 'check' OR a.methodName CONTAINS 'Count')
          AND (b.methodName CONTAINS 'findAll' OR b.methodName CONTAINS 'getEmployees')
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_full_fetch_for_check)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 10:
            anomalies.append({
                "taxonomy_id": "T3",
                "category": "IMPROPER_FUNCTION_USAGE",
                "type": "FULL_FETCH_FOR_EXISTENCE_CHECK",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' fetches full entity graph via '{callee}' to check existence or count ({count} samples). Replace with existsBy...() or COUNT query."
            })

    return anomalies


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
