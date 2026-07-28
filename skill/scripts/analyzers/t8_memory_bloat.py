#!/usr/bin/env python3
"""
T8. Перерасход памяти (Memory Bloat & Excessive Allocations)
Detects in-memory Stream filtering/pagination and string-allocation hotspots by real allocated
bytes (Allocation nodes, spec 002) rather than CALLS-edge call counts — see
plan/005-allocation-based-t4-t8.md. Structural matching (which methods do this at all) is still
CALLS-edge-based; only the inclusion threshold and severity are now byte-driven.
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

# Severity is relative to the whole profile's allocated bytes, not an absolute constant (spec 005).
_HIGH_SEVERITY_PERCENT = 5.0


def _total_allocated_bytes(conn) -> int:
    res = conn.execute("MATCH (a:Allocation) RETURN sum(a.bytes)")
    if res.has_next():
        total = res.get_next()[0]
        return int(total) if total is not None else 0
    return 0


def _caller_allocated_bytes(conn, method_id: str) -> int:
    """
    Sum of Allocation.bytes attributable to a method's call subtree. Allocation nodes are only
    linked (via ALLOCATED_BY) to the *leaf* frame where the allocation actually happened — which
    is almost never the CALLS-matched "caller" itself (that caller is usually several frames above
    the real allocation site). So this walks forward through CALLS to any reachable leaf that has
    allocations, not just a direct single-hop match. DISTINCT is required: multiple call paths to
    the same leaf would otherwise double-count the same Allocation node once per path.
    """
    res = conn.execute(
        """
        MATCH (m:Method {id: $mid})-[:CALLS*0..10]->(leaf:Method)<-[:ALLOCATED_BY]-(alloc:Allocation)
        WITH DISTINCT alloc
        RETURN sum(alloc.bytes)
        """,
        {"mid": method_id},
    )
    if res.has_next():
        total = res.get_next()[0]
        return int(total) if total is not None else 0
    return 0


def _severity_for_bytes(caller_bytes: int, total_bytes: int) -> str:
    if total_bytes <= 0:
        return "MEDIUM"
    percent = (caller_bytes / total_bytes) * 100
    return "HIGH" if percent > _HIGH_SEVERITY_PERCENT else "MEDIUM"


def analyze_t8(conn) -> list:
    anomalies = []
    total_allocated_bytes = _total_allocated_bytes(conn)

    # 1. In-Memory Stream Filtering / Pagination — structural match stays the same; the finding
    # is now gated and scored on how many bytes the caller actually allocated, not on edge count.
    query_stream_filter = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'ReferencePipeline' OR b.methodName CONTAINS 'filter' OR b.methodName CONTAINS 'accept'
        RETURN a.id AS caller_id, a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_stream_filter)
    while res.has_next():
        caller_id, caller, callee, count, pct = res.get_next()
        caller_bytes = _caller_allocated_bytes(conn, caller_id)
        if caller_bytes > 0:
            anomalies.append({
                "taxonomy_id": "T8",
                "category": "MEMORY_BLOAT",
                "type": "IN_MEMORY_FILTERING",
                "severity": _severity_for_bytes(caller_bytes, total_allocated_bytes),
                "caller": caller,
                "callee": callee,
                "sample_count": caller_bytes,
                "percentage": pct,
                "description": f"Method '{caller}' processes datasets in JVM memory via Streams, allocating {caller_bytes} bytes in this run. Delegate WHERE/LIMIT filtering to SQL database.",
            })

    # 2. String Concatenation Allocation Pressure — same treatment.
    query_string_concat = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'StringBuilder' OR (b.className CONTAINS 'String' AND b.methodName CONTAINS 'concat')
        RETURN a.id AS caller_id, a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_string_concat)
    while res.has_next():
        caller_id, caller, callee, count, pct = res.get_next()
        caller_bytes = _caller_allocated_bytes(conn, caller_id)
        if caller_bytes > 0:
            anomalies.append({
                "taxonomy_id": "T8",
                "category": "MEMORY_BLOAT",
                "type": "EXCESSIVE_STRING_ALLOCATIONS",
                "severity": _severity_for_bytes(caller_bytes, total_allocated_bytes),
                "caller": caller,
                "callee": callee,
                "sample_count": caller_bytes,
                "percentage": pct,
                "description": f"Excessive string allocation/concatenation in '{caller}', allocating {caller_bytes} bytes in this run. High GC allocation pressure.",
            })

    # 3. Contract-bounded request collection (ND-4) now lives in rules/graph_rules.yaml (spec 010).
    anomalies.extend(rule_engine.run(conn, "T8"))

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
