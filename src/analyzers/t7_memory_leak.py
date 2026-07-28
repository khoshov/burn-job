#!/usr/bin/env python3
"""
T7. Утечка памяти (Memory Leaks)
Detects real retained-object accumulation (jdk.OldObjectSample events, spec 002) and, when the
database holds more than one profiling run, a genuine cross-run growth trend — direct evidence of
a leak rather than a same-run heuristic. See plan/006-leak-detection-t7.md.
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

# RETAINED_OBJECT_ACCUMULATION: any confirmed OldObjectSample is real evidence (unlike a CPU-count
# proxy, this doesn't need many samples to be meaningful) — severity scales with how old/how many.
_RETAINED_CRITICAL_AGE_MS = 1000
_RETAINED_CRITICAL_COUNT = 5


def _retained_object_findings(conn) -> list:
    anomalies = []
    res = conn.execute(
        """
        MATCH (r:RetainedObject)-[:RETAINED_BY]->(m:Method)
        RETURN m.className + '.' + m.methodName AS method, r.className AS objClass,
               count(r) AS retainedCount, avg(r.ageMs) AS avgAge
        """
    )
    while res.has_next():
        method, obj_class, retained_count, avg_age = res.get_next()
        retained_count = int(retained_count)
        avg_age = float(avg_age) if avg_age is not None else 0.0
        if retained_count < 1:
            continue
        severity = "CRITICAL" if (avg_age > _RETAINED_CRITICAL_AGE_MS or retained_count > _RETAINED_CRITICAL_COUNT) else "HIGH"
        anomalies.append({
            "taxonomy_id": "T7",
            "category": "MEMORY_LEAK",
            "type": "RETAINED_OBJECT_ACCUMULATION",
            "severity": severity,
            "caller": "OldGen Garbage Collector",
            "callee": method,
            "sample_count": retained_count,
            "percentage": 0.0,
            "description": (
                f"'{obj_class}' instances retained across GC cycles at '{method}' "
                f"({retained_count} sampled objects, avg age {avg_age:.0f}ms). "
                f"Risk of unbounded memory leak / OutOfMemoryError."
            ),
        })
    return anomalies


def _growth_trend_findings(conn) -> list:
    """
    Compares RetainedObject counts for the same (method, objClass) across every distinct runId
    present in the database, ordered by the Run node's timestamp. A method whose retained count
    rises monotonically (non-decreasing at every step, strictly higher at the end than the start)
    across 2+ runs is direct, measured proof of a growing leak — not an inference from one snapshot.
    """
    res = conn.execute(
        """
        MATCH (r:RetainedObject)-[:RETAINED_BY]->(m:Method)
        OPTIONAL MATCH (run:Run {id: r.runId})
        RETURN m.className + '.' + m.methodName AS method, r.className AS objClass,
               r.runId AS runId, run.timestamp AS ts, count(r) AS cnt
        """
    )

    series: dict = {}  # (method, objClass) -> list of (sort_key, runId, cnt)
    while res.has_next():
        method, obj_class, run_id, ts, cnt = res.get_next()
        key = (method, obj_class)
        sort_key = ts if ts is not None else run_id  # fall back to runId string ordering if Run node is missing
        series.setdefault(key, []).append((sort_key, run_id, int(cnt)))

    anomalies = []
    for (method, obj_class), points in series.items():
        distinct_runs = {run_id for _, run_id, _ in points}
        if len(distinct_runs) < 2:
            continue
        points.sort(key=lambda p: p[0])
        counts = [cnt for _, _, cnt in points]
        is_non_decreasing = all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1))
        is_growing = is_non_decreasing and counts[-1] > counts[0]
        if not is_growing:
            continue
        anomalies.append({
            "taxonomy_id": "T7",
            "category": "MEMORY_LEAK",
            "type": "UNBOUNDED_GROWTH_TREND",
            "severity": "CRITICAL",
            "caller": "Cross-Run Retention Trend",
            "callee": method,
            "sample_count": counts[-1] - counts[0],
            "percentage": 0.0,
            "description": (
                f"Retained '{obj_class}' count for '{method}' grew monotonically across "
                f"{len(distinct_runs)} profiling runs ({counts[0]} -> {counts[-1]}). "
                f"This is a measured growth trend, not a single-run inference."
            ),
        })
    return anomalies


def analyze_t7(conn) -> list:
    anomalies = []
    anomalies.extend(_retained_object_findings(conn))
    anomalies.extend(_growth_trend_findings(conn))

    # UNBOUNDED_CACHE_OR_COLLECTION_GROWTH (the cheaper, weaker, single-run CALLS-count signal —
    # see plan/006) now lives in rules/graph_rules.yaml (spec 010).
    anomalies.extend(rule_engine.run(conn, "T7"))

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
