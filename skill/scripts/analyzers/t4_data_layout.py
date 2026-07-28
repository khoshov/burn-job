#!/usr/bin/env python3
"""
T4. Ошибки в раскладке данных (Data Layout & Object Overhead)
Detects excessive object wrapper overhead via real allocation bytes (not CPU-sample-count proxy,
see plan/005-allocation-based-t4-t8.md), plus a static (source-level) field-padding heuristic that
requires no application run at all.
"""

import sys
import os
import argparse
import json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_ROOT = os.path.dirname(_SCRIPT_DIR)
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False

import rule_engine  # noqa: E402
from object_layout import compute_layout_for_source_file  # noqa: E402
from source_mapping import _class_index  # noqa: E402

# Absolute byte thresholds for BOXED_WRAPPER_OVERHEAD (spec 005: T4 keeps an absolute threshold,
# unlike T8's percentage-of-profile approach).
_BOXED_OVERHEAD_MIN_BYTES = 10_000
_BOXED_OVERHEAD_HIGH_BYTES = 100_000


def analyze_t4(conn) -> list:
    # ARRAY_ALLOCATION_PRESSURE now lives in rules/graph_rules.yaml (spec 010).
    anomalies = rule_engine.run(conn, "T4")

    # 1. High Allocation Pressure on Primitive Wrappers — real bytes from JFR allocation
    # sampling (Allocation nodes, spec 002), not a count of Integer.valueOf/Long.valueOf calls.
    query_boxed_allocations = """
        MATCH (a:Allocation)-[:ALLOCATED_BY]->(m:Method)
        WHERE a.className CONTAINS 'Integer' OR a.className CONTAINS 'Long'
        RETURN m.className + '.' + m.methodName AS method, sum(a.bytes) AS totalBytes
        ORDER BY totalBytes DESC
    """
    res = conn.execute(query_boxed_allocations)
    while res.has_next():
        method, total_bytes = res.get_next()
        total_bytes = int(total_bytes) if total_bytes is not None else 0
        if total_bytes > _BOXED_OVERHEAD_MIN_BYTES:
            severity = "HIGH" if total_bytes > _BOXED_OVERHEAD_HIGH_BYTES else "MEDIUM"
            anomalies.append({
                "taxonomy_id": "T4",
                "category": "DATA_LAYOUT",
                "type": "BOXED_WRAPPER_OVERHEAD",
                "severity": severity,
                "caller": "Allocation Profiler",
                "callee": method,
                "sample_count": total_bytes,
                "percentage": 0.0,
                "description": f"'{method}' allocated {total_bytes} bytes of boxed Integer/Long wrapper objects in this run.",
            })

    # 2. WASTED_FIELD_PADDING — static heuristic over src/main/java, no application run required.
    # See object_layout.py's module docstring for the ND-1 caveat this rule deliberately respects:
    # this flags source declarations that are suboptimal *as written*, not a confirmed runtime cost.
    for class_fqn, file_rel_path in _class_index().items():
        simple_name = class_fqn.rsplit(".", 1)[-1]
        abs_path = os.path.join(_SCRIPTS_ROOT, "..", "..", file_rel_path)
        try:
            layout = compute_layout_for_source_file(abs_path, simple_name)
        except Exception:
            continue
        if layout["wasted_bytes"] > 0:
            anomalies.append({
                "taxonomy_id": "T4",
                "category": "DATA_LAYOUT",
                "type": "WASTED_FIELD_PADDING",
                "severity": "LOW",
                "caller": "Static Field-Layout Analysis",
                "callee": class_fqn,
                "sample_count": layout["wasted_bytes"],
                "percentage": 0.0,
                "description": (
                    f"Class '{class_fqn}' declares fields in an order that heuristically wastes "
                    f"~{layout['wasted_bytes']} bytes/instance vs. a size-descending order "
                    f"{layout['optimal_order']} (static estimate — HotSpot may already reorder "
                    f"fields at runtime; confirm with a real JOL measurement before treating this "
                    f"as a confirmed defect, per non_defects.py ND-1)."
                ),
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
