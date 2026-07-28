#!/usr/bin/env python3
"""
Call Graph Differential Analyzer for KùzuDB.
Compares two profiling runs (e.g. base run vs current run / commit A vs commit B)
to detect performance regressions, improvements, new hotspots, and structural call changes.
"""

import sys
import os
import argparse
import json
from collections import defaultdict

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def compare_runs(db_path: str, base_run_id: str, target_run_id: str, threshold_pct: float = 20.0):
    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"Error: KùzuDB database path '{db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # 1. Fetch calls for base_run
    base_calls = {}
    res = conn.execute("""
        MATCH (a:Method)-[r:CALLS {runId: $rid}]->(b:Method)
        RETURN a.id + ' -> ' + b.id AS edge_id, a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
    """, {"rid": base_run_id})
    while res.has_next():
        edge_id, caller, callee, count, percent = res.get_next()
        base_calls[edge_id] = {
            "caller": caller,
            "callee": callee,
            "count": count,
            "percent": percent
        }

    # 2. Fetch calls for target_run
    target_calls = {}
    res = conn.execute("""
        MATCH (a:Method)-[r:CALLS {runId: $rid}]->(b:Method)
        RETURN a.id + ' -> ' + b.id AS edge_id, a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
    """, {"rid": target_run_id})
    while res.has_next():
        edge_id, caller, callee, count, percent = res.get_next()
        target_calls[edge_id] = {
            "caller": caller,
            "callee": callee,
            "count": count,
            "percent": percent
        }

    regressions = []
    improvements = []
    new_calls = []
    removed_calls = []

    all_keys = set(base_calls.keys()).union(set(target_calls.keys()))

    for key in all_keys:
        in_base = key in base_calls
        in_target = key in target_calls

        if in_base and in_target:
            b_item = base_calls[key]
            t_item = target_calls[key]

            b_cnt = b_item["count"]
            t_cnt = t_item["count"]

            diff_cnt = t_cnt - b_cnt
            pct_change = round(((t_cnt - b_cnt) / max(1, b_cnt)) * 100, 2)

            item = {
                "edge": key,
                "caller": t_item["caller"],
                "callee": t_item["callee"],
                "base_count": b_cnt,
                "target_count": t_cnt,
                "diff_count": diff_cnt,
                "pct_change": pct_change
            }

            if pct_change >= threshold_pct:
                regressions.append(item)
            elif pct_change <= -threshold_pct:
                improvements.append(item)

        elif in_target and not in_base:
            t_item = target_calls[key]
            new_calls.append({
                "edge": key,
                "caller": t_item["caller"],
                "callee": t_item["callee"],
                "target_count": t_item["count"],
                "target_percent": t_item["percent"]
            })
        elif in_base and not in_target:
            b_item = base_calls[key]
            removed_calls.append({
                "edge": key,
                "caller": b_item["caller"],
                "callee": b_item["callee"],
                "base_count": b_item["count"],
                "base_percent": b_item["percent"]
            })

    # Sort results
    regressions.sort(key=lambda x: x["pct_change"], reverse=True)
    improvements.sort(key=lambda x: x["pct_change"])

    return {
        "base_run_id": base_run_id,
        "target_run_id": target_run_id,
        "summary": {
            "total_regressions": len(regressions),
            "total_improvements": len(improvements),
            "total_new_calls": len(new_calls),
            "total_removed_calls": len(removed_calls)
        },
        "regressions": regressions,
        "improvements": improvements,
        "new_calls": new_calls,
        "removed_calls": removed_calls
    }


def format_diff_report(diff_result: dict) -> str:
    lines = [
        f"### PROFILER DIFFERENTIAL ANALYSIS REPORT",
        f"- **Base Run (Before):** `{diff_result['base_run_id']}`",
        f"- **Target Run (After):** `{diff_result['target_run_id']}`",
        f"- **Summary:** {diff_result['summary']['total_regressions']} Regressions | {diff_result['summary']['total_improvements']} Improvements | {diff_result['summary']['total_new_calls']} New Call Paths | {diff_result['summary']['total_removed_calls']} Eliminated Call Paths\n"
    ]

    if diff_result["regressions"]:
        lines.append("#### 🔴 PERFORMANCE REGRESSIONS (> THRESHOLD)")
        for item in diff_result["regressions"]:
            lines.append(f"- **`{item['caller']}` -> `{item['callee']}`**")
            lines.append(f"  - Count: {item['base_count']} samples ➔ {item['target_count']} samples (**+{item['pct_change']}%**)")

    if diff_result["improvements"]:
        lines.append("\n#### 🟢 PERFORMANCE IMPROVEMENTS")
        for item in diff_result["improvements"]:
            lines.append(f"- **`{item['caller']}` -> `{item['callee']}`**")
            lines.append(f"  - Count: {item['base_count']} samples ➔ {item['target_count']} samples (**{item['pct_change']}%**)")

    if diff_result["new_calls"]:
        lines.append("\n#### 🆕 NEW CALL PATHS INTRODUCED")
        for item in diff_result["new_calls"]:
            lines.append(f"- **`{item['caller']}` -> `{item['callee']}`** ({item['target_count']} samples, {item['target_percent']}%)")

    if diff_result["removed_calls"]:
        lines.append("\n#### 🗑️ ELIMINATED / OPTIMIZED OUT CALL PATHS")
        for item in diff_result["removed_calls"]:
            lines.append(f"- **`{item['caller']}` -> `{item['callee']}`** (Was {item['base_count']} samples)")

    lines.append("\n### INSTRUCTIONS FOR LLM:")
    lines.append("1. Analyze the regressions and structural call changes above.")
    lines.append("2. Explain why the execution time / sample counts degraded or improved.")
    lines.append("3. Provide code refactoring recommendations for identified regressions.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare two profiling runs in KùzuDB to detect regressions and improvements")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder")
    parser.add_argument("--base-run", required=True, help="Base run ID (before change / main branch)")
    parser.add_argument("--target-run", required=True, help="Target run ID (after change / feature branch)")
    parser.add_argument("--threshold", type=float, default=20.0, help="Min percentage change to flag as regression/improvement (default: 20.0%)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON diff object")

    args = parser.parse_args()

    diff_result = compare_runs(args.db_path, args.base_run, args.target_run, args.threshold)

    if args.json:
        print(json.dumps(diff_result, indent=2))
        return

    print("=========================================================")
    print("       CALL GRAPH DIFFERENTIAL REPORT (KÙZU DB)          ")
    print("=========================================================\n")
    print(format_diff_report(diff_result))


if __name__ == "__main__":
    main()
