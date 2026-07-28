#!/usr/bin/env python3
"""
T4. Ошибки в раскладке данных (Data Layout & Object Overhead)
Detects excessive object wrapper overhead (Integer / Long boxing), heavy primitive boxing in collections,
and allocation pressure from suboptimal structures.
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


def analyze_t4(conn) -> list:
    anomalies = []

    # 1. High Allocation Pressure on Primitive Wrappers & Map Nodes
    query_boxed_allocations = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE (b.className CONTAINS 'Integer' AND b.methodName = 'valueOf')
           OR (b.className CONTAINS 'Long' AND b.methodName = 'valueOf')
           OR (b.className CONTAINS 'HashMap$Node')
           OR (b.className CONTAINS 'ArrayList' AND b.methodName = 'grow')
           OR (b.className CONTAINS 'ClassLayout' OR b.methodName CONTAINS 'parseInstance')
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_boxed_allocations)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 5:
            is_jol = "jol" in callee.lower() or "classlayout" in callee.lower()
            anomalies.append({
                "taxonomy_id": "T4",
                "category": "DATA_LAYOUT",
                "type": "BOXED_WRAPPER_OVERHEAD",
                "severity": "LOW" if is_jol else "MEDIUM",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Field order inspection JOL padding in '{caller}' -> '{callee}' ({count} samples)." if is_jol else f"High allocation overhead in '{caller}' creating boxed primitives ({count} samples)."
            })


    # 2. Heavy DTO / Entity memory layout allocations
    query_heavy_layout = """
        MATCH (m:Method)
        WHERE m.className CONTAINS 'byte[]' OR m.className CONTAINS 'Object[]' OR m.className CONTAINS 'char[]'
        RETURN m.className + '.' + m.methodName AS method, m.sampleCount
        ORDER BY m.sampleCount DESC
    """
    res = conn.execute(query_heavy_layout)
    while res.has_next():
        method, count = res.get_next()
        if count > 100:
            anomalies.append({
                "taxonomy_id": "T4",
                "category": "DATA_LAYOUT",
                "type": "ARRAY_ALLOCATION_PRESSURE",
                "severity": "MEDIUM",
                "caller": "JVM Garbage Collector",
                "callee": method,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Massive array allocation footprint detected in '{method}' ({count} samples). Suboptimal buffer or string padding layout."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T4 Analyzer: Data layout errors & allocation footprint")
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
    results = analyze_t4(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T4. DATA LAYOUT & ALLOCATION FOOTPRINT REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
