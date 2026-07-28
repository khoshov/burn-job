#!/usr/bin/env python3
"""
T9. Избыточная нагрузка на CPU (Excessive CPU Load & Hot Paths)
Detects CPU hotspot methods, excessive work in hot paths, and real thread lock/park contention
(MonitorBlock nodes, spec 002) — see plan/007-lock-contention-t9-and-regex-fix.md.
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


def analyze_t9(conn) -> list:
    anomalies = []

    # 1. Thread Lock Contention & Parking — real blocked duration (jdk.JavaMonitorEnter /
    # jdk.ThreadPark events, spec 002), not a guess from "Lock"/"park"/"synchronized" in a name.
    query_lock_contention = """
        MATCH (b:MonitorBlock)-[:BLOCKED_IN]->(m:Method)
        RETURN m.className + '.' + m.methodName AS method, sum(b.durationMs) AS totalBlockedMs, count(b) AS blockCount
        ORDER BY totalBlockedMs DESC
    """
    res = conn.execute(query_lock_contention)
    while res.has_next():
        method, total_blocked_ms, block_count = res.get_next()
        total_blocked_ms = int(total_blocked_ms) if total_blocked_ms is not None else 0
        block_count = int(block_count)
        if total_blocked_ms > 100:
            severity = "HIGH" if total_blocked_ms > 500 else "MEDIUM"
            anomalies.append({
                "taxonomy_id": "T9",
                "category": "CPU_LOAD",
                "type": "THREAD_LOCK_CONTENTION",
                "severity": severity,
                "caller": "Thread Contention Monitor",
                "callee": method,
                "sample_count": total_blocked_ms,
                "percentage": 0.0,
                "description": f"'{method}' spent {total_blocked_ms}ms blocked across {block_count} monitor/park events. Thread pool bottleneck.",
            })

    # 2. CPU_HOTSPOT_METHOD and 3. MICROBENCHMARK_REGEX_COMPILE (with its Global-frame exclusion
    # and count threshold, spec 007) now live in rules/graph_rules.yaml (spec 010).
    anomalies.extend(rule_engine.run(conn, "T9"))

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
