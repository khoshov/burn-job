#!/usr/bin/env python3
"""
T9. Избыточная нагрузка на CPU (Excessive CPU Load & Hot Paths)
Detects CPU hotspot methods, excessive work in hot paths, and thread lock contention.
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


def analyze_t9(conn) -> list:
    anomalies = []

    # 1. Thread Lock Contention & Parking
    query_lock_contention = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'Lock' OR b.methodName CONTAINS 'park' OR b.methodName CONTAINS 'synchronized'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_lock_contention)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 30:
            anomalies.append({
                "taxonomy_id": "T9",
                "category": "CPU_LOAD",
                "type": "THREAD_LOCK_CONTENTION",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Thread contention or locking block in '{caller}' ({count} samples). Thread pool bottleneck."
            })

    # 2. Top CPU Hotspot Methods (High sample count spike)
    query_cpu_hotspots = """
        MATCH (m:Method)
        WHERE (m.className STARTS WITH 'com.example' OR m.className STARTS WITH 'examples') AND m.sampleCount > 100
        RETURN m.className + '.' + m.methodName AS method, m.sampleCount
        ORDER BY m.sampleCount DESC
        LIMIT 10
    """

    res = conn.execute(query_cpu_hotspots)
    while res.has_next():
        method, count = res.get_next()
        anomalies.append({
            "taxonomy_id": "T9",
            "category": "CPU_LOAD",
            "type": "CPU_HOTSPOT_METHOD",
            "severity": "MEDIUM",
            "caller": "Hot Execution Path",
            "callee": method,
            "sample_count": count,
            "percentage": 0.0,
            "description": f"Hotspot method '{method}' consumed {count} CPU samples. Optimize heavy loop logic or caching."
        })

    # 3. Microbenchmark noise regex compilation
    query_regex_compile = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'Pattern' OR b.methodName CONTAINS 'compile'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_regex_compile)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        anomalies.append({
            "taxonomy_id": "T9",
            "category": "CPU_LOAD",
            "type": "MICROBENCHMARK_REGEX_COMPILE",
            "severity": "LOW",
            "caller": caller,
            "callee": callee,
            "sample_count": count,
            "percentage": pct,
            "description": f"Microbenchmark noise pattern.compile in '{caller}' -> '{callee}' ({count} samples)."
        })


    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T9 Analyzer: Excessive CPU load and hotspots")
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
    results = analyze_t9(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T9. EXCESSIVE CPU LOAD REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
