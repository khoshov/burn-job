"""
Performance Anomaly Orchestrator for KuzuDB Call Graphs.
Runs modular category analyzers (T1 - T9) to detect performance antipatterns
across CPU, DB, Memory, Concurrency, Algorithms, Data Layout, and Code Structure.

Combines graph database (KuzuDB) profiling data with static source analysis
for cross-validated, higher-confidence findings.
"""

import sys
import os
import argparse
import json
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False

from burn_job.detectors.callgraph import build_static_call_graph, compute_reachable
from burn_job.detectors.differential import compare_runs, list_run_ids
from burn_job.detectors import patterns as static_patterns
from burn_job.detectors.patterns import (
    detect_n_plus_one,
    detect_existence_check_full_fetch,
    detect_nested_loops,
    detect_duplicate_methods,
    detect_boxed_wrapper_overhead,
    detect_redundant_null_checks,
    detect_unbatched_save_loop,
    detect_unbounded_static_map,
    detect_in_memory_stream_filtering,
    detect_cpu_hotspot_patterns,
    gather_non_defect_candidates,
)
from burn_job.detectors.taxonomy.t1_redundant_ops import analyze_t1
from burn_job.detectors.taxonomy.t2_inefficient_algos import analyze_t2
from burn_job.detectors.taxonomy.t3_improper_func_usage import analyze_t3
from burn_job.detectors.taxonomy.t4_data_layout import analyze_t4
from burn_job.detectors.taxonomy.t5_redundant_checks import analyze_t5
from burn_job.detectors.taxonomy.t6_db_queries import analyze_t6
from burn_job.detectors.taxonomy.t7_memory_leak import analyze_t7
from burn_job.detectors.taxonomy.t8_memory_bloat import analyze_t8
from burn_job.detectors.taxonomy.t9_cpu_hotspots import analyze_t9
from burn_job.detectors.non_defects import annotate_report_with_non_defects
from burn_job.detectors._shared import SRC_ROOT, iter_java_files, read_file, strip_comments, iter_method_bodies


ANALYZER_REGISTRY = {
    "T1": analyze_t1,
    "T2": analyze_t2,
    "T3": analyze_t3,
    "T4": analyze_t4,
    "T5": analyze_t5,
    "T6": analyze_t6,
    "T7": analyze_t7,
    "T8": analyze_t8,
    "T9": analyze_t9,
}

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLASSPATH_DIR = os.path.join(_THIS_DIR, "..", "..", "..", "..", "java", "target", "classes")

STATIC_PATTERN_DETECTORS = {
    "T1": detect_duplicate_methods,
    "T2": detect_nested_loops,
    "T3": detect_existence_check_full_fetch,
    "T4": detect_boxed_wrapper_overhead,
    "T5": detect_redundant_null_checks,
    "T6": detect_unbatched_save_loop,
    "T7": detect_unbounded_static_map,
    "T8": detect_in_memory_stream_filtering,
    "T9": detect_cpu_hotspot_patterns,
}


def compute_confidence(anomaly: dict, static_match: bool = False,
                       graph_evidence: bool = False,
                       cross_run_diff: bool = False) -> float:
    evidence_count = sum([static_match, graph_evidence, cross_run_diff])
    if evidence_count >= 2:
        base = 0.7 + (evidence_count - 2) * 0.1
    elif evidence_count == 1:
        base = 0.5
    else:
        base = 0.3
    if anomaly.get("severity") in ("CRITICAL", "HIGH"):
        base = min(base + 0.1, 0.95)
    if anomaly.get("percentage", 0) > 5.0:
        base = min(base + 0.1, 0.95)
    return round(base, 2)


def _run_graph_analyzers(conn, target_keys: list,
                         reachable_methods=None, declared_methods=None) -> list:
    anomalies = []
    for key in target_keys:
        key_upper = key.upper()
        if key_upper not in ANALYZER_REGISTRY:
            continue
        fn = ANALYZER_REGISTRY[key_upper]
        if key_upper == "T5":
            results = fn(conn, reachable_methods=reachable_methods, declared_methods=declared_methods)
        else:
            results = fn(conn)
        for a in results:
            a["_source"] = "graph"
        anomalies.extend(results)
    return anomalies


def _run_static_patterns(target_keys: list) -> list:
    anomalies = []
    for key in target_keys:
        key_upper = key.upper()
        if key_upper in STATIC_PATTERN_DETECTORS:
            results = STATIC_PATTERN_DETECTORS[key_upper]()
            for a in results:
                a["_source"] = "static"
            anomalies.extend(results)
    return anomalies


def _build_source_method_index() -> Dict[str, List[Tuple[str, int]]]:
    index = defaultdict(list)
    src_root = SRC_ROOT
    if not os.path.isdir(src_root):
        return index
    for path in iter_java_files(src_root):
        text = read_file(path)
        clean = strip_comments(text)
        rel_path = os.path.relpath(path, REPO_ROOT)
        for method_name, body, start_line in iter_method_bodies(text):
            index[method_name].append((rel_path, start_line))
    return dict(index)


def _method_identity(anomaly: dict) -> str:
    return f"{anomaly.get('type', '')}|{anomaly.get('callee', '')}"


def _merge_dual_evidence(static_anomalies: List[dict],
                          graph_anomalies: List[dict]) -> List[dict]:
    static_by_key = defaultdict(list)
    for a in static_anomalies:
        static_by_key[_method_identity(a)].append(a)
    graph_by_key = defaultdict(list)
    for a in graph_anomalies:
        graph_by_key[_method_identity(a)].append(a)

    merged = []
    for key in set(static_by_key) | set(graph_by_key):
        static_list = static_by_key.get(key, [])
        graph_list = graph_by_key.get(key, [])

        if static_list and graph_list:
            primary = graph_list[0]
            static_src = static_list[0]
            primary["_dual_evidence"] = True
            primary["_approaches"] = ["graph", "static"]
            primary["evidence_detail"] = {
                "graph": {
                    "sample_count": primary.get("sample_count", 0),
                    "percentage": primary.get("percentage", 0),
                    "description": primary.get("description", ""),
                },
                "static": {
                    "source_location": f"{static_src.get('caller', '')}",
                    "description": static_src.get("description", ""),
                },
            }
            primary["sample_count"] = primary.get("sample_count", 0) + static_src.get("sample_count", 0)
            primary["description"] = (
                f"[Dual evidence: graph + static] "
                f"{static_src.get('description', '')} "
                f"(confirmed by profiling: {primary.get('sample_count', 0)} samples, "
                f"{primary.get('percentage', 0):.1f}%)"
            )
            primary["confidence"] = compute_confidence(primary, static_match=True, graph_evidence=True)
            merged.append(primary)
        elif graph_list and not static_list:
            a = graph_list[0]
            a["_dual_evidence"] = False
            a["_approaches"] = ["graph"]
            a["confidence"] = compute_confidence(a, static_match=False, graph_evidence=True)
            merged.append(a)
        elif static_list and not graph_list:
            a = static_list[0]
            a["_dual_evidence"] = False
            a["_approaches"] = ["static"]
            a["confidence"] = compute_confidence(a, static_match=True, graph_evidence=False)
            merged.append(a)
    return merged


def analyze_anomalies(db_path: str, selected_categories: list = None,
                      annotate_non_defects: bool = True,
                      classpath_dir: str = DEFAULT_CLASSPATH_DIR,
                      cross_reference: bool = True) -> list:
    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)
    if not os.path.exists(db_path):
        print(f"Error: KuzuDB database path '{db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    target_keys = selected_categories if selected_categories else list(ANALYZER_REGISTRY.keys())

    reachable_methods = declared_methods = None
    if "T5" in [k.upper() for k in target_keys] and classpath_dir and os.path.isdir(classpath_dir):
        call_graph, entry_points = build_static_call_graph(classpath_dir)
        declared_methods = set(call_graph.keys())
        reachable_methods = compute_reachable(call_graph, entry_points)

    graph_anomalies = _run_graph_analyzers(conn, target_keys, reachable_methods, declared_methods)
    static_anomalies = _run_static_patterns(target_keys)
    static_anomalies += gather_non_defect_candidates()

    if cross_reference:
        all_anomalies = _merge_dual_evidence(static_anomalies, graph_anomalies)
    else:
        all_anomalies = list(graph_anomalies) + list(static_anomalies)

    if annotate_non_defects:
        context = {"growth_status": _build_growth_status(conn)}
        all_anomalies = annotate_report_with_non_defects(all_anomalies, context)

    for a in all_anomalies:
        if "confidence" not in a:
            a["confidence"] = compute_confidence(a)

    return all_anomalies


def _build_growth_status(conn) -> dict:
    run_ids = list_run_ids(conn)
    if len(run_ids) != 2:
        return {}
    diffs = compare_runs(conn, run_ids[0], run_ids[1])
    status = {}
    for d in diffs:
        if d["metric"] != "RetainedObject.count":
            continue
        status[d["method"]] = "growing" if (d["delta_pct"] or 0) > 0 else "stable"
    return status


def format_llm_prompt(anomalies: list) -> str:
    defects = [a for a in anomalies if a.get("status") != "NON_DEFECT"]
    non_defects = [a for a in anomalies if a.get("status") == "NON_DEFECT"]
    dual_count = sum(1 for a in defects if a.get("_dual_evidence"))
    graph_only = sum(1 for a in defects if a.get("_approaches") == ["graph"])
    static_only = sum(1 for a in defects if a.get("_approaches") == ["static"])

    prompt = [
        "### AUTOMATED PERFORMANCE ANOMALY REPORT (DUAL-APPROACH: GRAPH DB + STATIC ANALYSIS)",
        f"Analyzed findings: {len(defects)} True Defects | {len(non_defects)} Marked Non-Defects\n",
        f"**Detection Breakdown:**",
        f"- Dual evidence (graph + static): {dual_count}",
        f"- Graph DB only: {graph_only}",
        f"- Static analysis only: {static_only}\n",
    ]

    if defects:
        prompt.append("#### DEFECTS REQUIRING ATTENTION:")
        for idx, item in enumerate(defects, 1):
            confidence = item.get("confidence", "N/A")
            approaches = item.get("_approaches", [])
            badge = {
                ("graph", "static"): "[GRAPH+STATIC]",
                ("graph",): "[GRAPH]",
                ("static",): "[STATIC]",
            }.get(tuple(approaches), "")
            dual_tag = " \u2605 DUAL EVIDENCE" if item.get("_dual_evidence") else ""
            prompt.append(f"**Anomaly #{idx}: {badge} [{item.get('taxonomy_id', 'TAX')}] {item['type']} [{item['severity']}] (Confidence: {confidence}){dual_tag}")
            prompt.append(f"- **Caller:** `{item['caller']}`")
            prompt.append(f"- **Callee:** `{item['callee']}`")
            prompt.append(f"- **Samples / Impact:** {item['sample_count']} samples")
            if "evidence_detail" in item:
                ed = item["evidence_detail"]
                if "graph" in ed:
                    prompt.append(f"- **Graph evidence:** {ed['graph']['sample_count']} samples ({ed['graph']['percentage']:.1f}%)")
                if "static" in ed:
                    prompt.append(f"- **Static evidence:** {ed['static']['source_location']}")
            prompt.append(f"- **Diagnosis:** {item['description']}\n")

    if non_defects:
        prompt.append("#### NON-DEFECTS / EXCLUDED BY RULES (SECTION 7):")
        for idx, item in enumerate(non_defects, 1):
            prompt.append(f"**Item #{idx}: [{item.get('non_defect_rule')}] {item.get('non_defect_title')}**")
            prompt.append(f"- **Candidate Method:** `{item['caller']}` -> `{item['callee']}`")
            prompt.append(f"- **Reason:** {item.get('non_defect_justification')}\n")

    prompt.append("### INSTRUCTIONS FOR LLM:")
    prompt.append("1. Prioritize dual-evidence findings (marked \u2605) -- they have both profiling data and source pattern confirmation.")
    prompt.append("2. Graph-only findings have profiling sample counts; investigate the described hot paths.")
    prompt.append("3. Static-only findings are structural patterns found in source; confirm via profiling if possible.")
    prompt.append("4. Provide refactored Java/Spring Boot code snippets resolving true defects.")

    return "\n".join(prompt)


def main():
    parser = argparse.ArgumentParser(description="Orchestrator for KuzuDB taxonomy performance analyzers (T1 - T9)")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KuzuDB database folder")
    parser.add_argument("--category", help="Comma-separated taxonomy IDs to run (e.g., T1,T2,T6). Default runs all.")
    parser.add_argument("--classpath-dir", default=DEFAULT_CLASSPATH_DIR, help="Compiled .class files for T5 static reachability check")
    parser.add_argument("--json", action="store_true", help="Output findings as raw JSON")
    parser.add_argument("--prompt-only", action="store_true", help="Output only formatted LLM prompt")
    parser.add_argument("--no-cross-ref", action="store_true", help="Skip cross-referencing; return separate lists")

    args = parser.parse_args()
    selected = [c.strip().upper() for c in args.category.split(",")] if args.category else None
    anomalies = analyze_anomalies(args.db_path, selected, classpath_dir=args.classpath_dir,
                                  cross_reference=not args.no_cross_ref)

    if args.json:
        print(json.dumps(anomalies, indent=2))
        return
    llm_prompt = format_llm_prompt(anomalies)
    if args.prompt_only:
        print(llm_prompt)
        return
    print("=========================================================")
    print("   DUAL-APPROACH ANOMALY REPORT (GRAPH DB + STATIC)     ")
    print("=========================================================\n")
    print(llm_prompt)


if __name__ == "__main__":
    main()
