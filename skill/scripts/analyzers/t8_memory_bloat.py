#!/usr/bin/env python3
"""
T8. Перерасход памяти (Memory Bloat & Excessive Allocations)
Detects in-memory Stream filtering/pagination and high transient object allocation pressure.
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


def analyze_t8(conn) -> list:
    anomalies = []

    # 1. In-Memory Stream Filtering / Pagination
    query_stream_filter = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'ReferencePipeline' OR b.methodName CONTAINS 'filter' OR b.methodName CONTAINS 'accept'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_stream_filter)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T8",
                "category": "MEMORY_BLOAT",
                "type": "IN_MEMORY_FILTERING",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' processes datasets in JVM memory via Streams ({count} samples). Delegate WHERE/LIMIT filtering to SQL database."
            })

    # 2. String Concatenation Allocation Pressure
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
                "taxonomy_id": "T8",
                "category": "MEMORY_BLOAT",
                "type": "EXCESSIVE_STRING_ALLOCATIONS",
                "severity": "MEDIUM",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Excessive string allocation/concatenation in '{caller}' ({count} samples). High GC allocation pressure."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T8 Analyzer: Memory bloat & transient allocations")
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
    results = analyze_t8(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T8. MEMORY BLOAT REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
