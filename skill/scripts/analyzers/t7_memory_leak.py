#!/usr/bin/env python3
"""
T7. Утечка памяти (Memory Leaks)
Detects unbounded memory growth, monotonically increasing live object samples, and static container retention.
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


def analyze_t7(conn) -> list:
    anomalies = []

    # 1. Old Gen retained objects & Live Object Samples (event=live profiling)
    query_retained_live_objects = """
        MATCH (m:Method)
        WHERE m.className CONTAINS 'OldObjectSample' OR m.className CONTAINS 'WeakHashMap'
           OR m.className CONTAINS 'ThreadLocal' OR m.className CONTAINS 'Static'
        RETURN m.className + '.' + m.methodName AS method, m.sampleCount
        ORDER BY m.sampleCount DESC
    """
    res = conn.execute(query_retained_live_objects)
    while res.has_next():
        method, count = res.get_next()
        if count > 20:
            anomalies.append({
                "taxonomy_id": "T7",
                "category": "MEMORY_LEAK",
                "type": "RETAINED_OBJECT_ACCUMULATION",
                "severity": "CRITICAL",
                "caller": "OldGen Garbage Collector",
                "callee": method,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Retained objects detected in '{method}' across GC cycles ({count} samples). Risk of unbounded memory leak / OutOfMemoryError."
            })

    # 2. Monotonically growing call edges across consecutive runs
    query_accumulating_edges = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE (b.className CONTAINS 'Map' OR b.className CONTAINS 'List' OR b.className CONTAINS 'Cache')
          AND b.methodName CONTAINS 'put' OR b.methodName CONTAINS 'add'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_accumulating_edges)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 100:
            anomalies.append({
                "taxonomy_id": "T7",
                "category": "MEMORY_LEAK",
                "type": "UNBOUNDED_CACHE_OR_COLLECTION_GROWTH",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"High rate of element addition to collection/cache in '{caller}' -> '{callee}' ({count} samples). Verify evictions / cleanup."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T7 Analyzer: Memory leaks")
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
    results = analyze_t7(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T7. MEMORY LEAK REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
