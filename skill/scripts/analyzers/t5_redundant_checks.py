#!/usr/bin/env python3
"""
T5. Избыточные проверки и блоки кода (Redundant Checks & Dead Code)
Detects genuinely dead code (static call-graph unreachability + zero runtime samples — spec 008)
plus repeated multi-layer validation calls. See plan/008-static-callgraph-reachability-t5.md for
why the old dynamic-only "sampleCount = 0" heuristic was unreliable in both directions: it flagged
untested-but-reachable code as dead, and its 'com.example'-prefix filter (dotted) never matched
this codebase's actual slash-separated className values, so it silently never fired at all.
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


def analyze_t5(conn, reachable_methods=None, declared_methods=None) -> list:
    anomalies = []

    # 1. Dead vs. merely-untested code — requires BOTH the static call graph (declared_methods,
    # reachable_methods from static_callgraph.py) and dynamic zero-sample evidence. Without a
    # static graph (e.g. the project hasn't been compiled) we skip this rule entirely rather than
    # risk a false DEAD_OR_UNREACHABLE_CODE claim from dynamic-only evidence.
    if declared_methods is not None and reachable_methods is not None:
        res = conn.execute("MATCH (m:Method) WHERE m.sampleCount = 0 RETURN m.id AS id, m.className + '.' + m.methodName AS method")
        while res.has_next():
            method_id, method_label = res.get_next()
            if method_id not in declared_methods:
                continue  # not project code (JDK/framework/etc.) — not ours to judge
            if method_id in reachable_methods:
                anomalies.append({
                    "taxonomy_id": "T5",
                    "category": "REDUNDANT_CHECKS",
                    "type": "UNTESTED_REACHABLE_CODE",
                    "severity": "LOW",
                    "caller": "Application Stack",
                    "callee": method_label,
                    "sample_count": 0,
                    "percentage": 0.0,
                    "description": f"'{method_label}' has 0 runtime samples but is statically reachable from a declared entry point (controller/main/@Test) — a test-coverage gap, not dead code.",
                })
            else:
                anomalies.append({
                    "taxonomy_id": "T5",
                    "category": "REDUNDANT_CHECKS",
                    "type": "DEAD_OR_UNREACHABLE_CODE",
                    "severity": "LOW",
                    "caller": "Application Stack",
                    "callee": method_label,
                    "sample_count": 0,
                    "percentage": 0.0,
                    "description": f"'{method_label}' has 0 runtime samples AND is statically unreachable from any declared entry point. Real dead-code candidate.",
                })

    # 2. Duplicate Validation Checks across Call Stack Layers
    query_duplicate_validation = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'ReferencePipeline' OR b.methodName CONTAINS 'accept'
           OR a.methodName CONTAINS 'toUpperCaseLoop' OR a.methodName CONTAINS 'formatCodeStyle'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count AS count
        ORDER BY r.count DESC
    """
    res = conn.execute(query_duplicate_validation)
    while res.has_next():
        caller, callee, count = res.get_next()
        if count > 1:
            is_style = "toUpperCaseLoop" in caller or "formatCodeStyle" in caller
            anomalies.append({
                "taxonomy_id": "T5",
                "category": "REDUNDANT_CHECKS",
                "type": "CODE_STYLE_FORMATTING" if is_style else "DUPLICATE_LAYER_VALIDATION",
                "severity": "LOW" if is_style else "MEDIUM",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": 0.0,
                "description": f"Formatting style code choice in '{caller}' -> '{callee}'." if is_style else f"In-memory stream validation in '{caller}' -> '{callee}' ({count} samples)."
            })


    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T5 Analyzer: Redundant checks and dead code")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder")
    parser.add_argument("--classpath-dir", help="Compiled .class files to build the static call graph from (e.g. target/classes); DEAD_OR_UNREACHABLE_CODE/UNTESTED_REACHABLE_CODE are skipped without it")
    parser.add_argument("--json", action="store_true", help="Output findings as JSON")
    args = parser.parse_args()

    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(args.db_path):
        print(f"Error: KùzuDB database path '{args.db_path}' does not exist.")
        sys.exit(1)

    reachable_methods = declared_methods = None
    if args.classpath_dir:
        _scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from static_callgraph import build_static_call_graph, compute_reachable

        call_graph, entry_points = build_static_call_graph(args.classpath_dir)
        declared_methods = set(call_graph.keys())
        reachable_methods = compute_reachable(call_graph, entry_points)

    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)
    results = analyze_t5(conn, reachable_methods=reachable_methods, declared_methods=declared_methods)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T5. REDUNDANT CHECKS & DEAD CODE REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
