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
from burn_job.detectors.patterns import (
    detect_n_plus_one,
    detect_existence_check_full_fetch,
    detect_nested_loops,
    detect_duplicate_methods,
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
from burn_job.detectors.composite import combine_all, compute_confidence
from burn_job.detectors._shared import SRC_ROOT, iter_java_files, read_file, strip_comments, iter_method_bodies, line_of

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
    "T6": detect_n_plus_one,
}


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
    """Build mapping from method name to (file_path, line) for all Java files."""
    index = defaultdict(list)
    src_root = SRC_ROOT
    if not os.path.isdir(src_root):
        return index
    for path in iter_java_files(src_root):
        text = read_file(path)
        clean = strip_comments(text)
        rel_path = os.path.relpath(path, os.path.join(_THIS_DIR, "..", "..", "..", ".."))
        for method_name, body, start_line in iter_method_bodies(text):
            index[method_name].append((rel_path, start_line))
    return dict(index)


def _resolve_fqn_to_source(fqn: str, method_index: Dict[str, List]) -> Optional[Tuple[str, int]]:
    """Resolve a fully qualified method name (e.g. com/example/Service.method) to (file, line)."""
    if "." in fqn and not fqn.startswith("com."):
        parts = fqn.rsplit(".", 1)
        method_name = parts[-1]
    elif "/" in fqn:
        parts = fqn.rsplit("/", 1)
        if "." in parts[-1]:
            inner = parts[-1].rsplit(".", 1)
            method_name = inner[-1]
        else:
            method_name = parts[-1]
    else:
        return None

    matches = method_index.get(method_name)
    if not matches:
        return None
    return matches[0]  # (file, line)


def _method_identity(anomaly: dict) -> str:
    """Canonical key: type + callee (the method where the defect lives)."""
    return f"{anomaly.get('type', '')}|{anomaly.get('callee', '')}"


def _merge_dual_evidence(static_anomalies: List[dict],
                          graph_anomalies: List[dict],
                          method_index: Dict[str, List]) -> List[dict]:
    """Merge findings by type+callee. When both static and graph detect the same
    issue in the same method, produce a single enriched finding with dual evidence."""
    static_by_key: Dict[str, List[dict]] = defaultdict(list)
    for a in static_anomalies:
        static_by_key[_method_identity(a)].append(a)

    graph_by_key: Dict[str, List[dict]] = defaultdict(list)
    for a in graph_anomalies:
        graph_by_key[_method_identity(a)].append(a)

    all_keys = set(static_by_key) | set(graph_by_key)
    merged = []

    for key in all_keys:
        static_list = static_by_key.get(key, [])
        graph_list = graph_by_key.get(key, [])

        if static_list and graph_list:
            # Both approaches agree: merge into a combined finding
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
            total_samples = primary.get("sample_count", 0) + static_src.get("sample_count", 0)
            primary["sample_count"] = total_samples
            primary["description"] = (
                f"[Dual evidence: graph + static] "
                f"{static_src.get('description', '')} "
                f"(confirmed by profiling: {primary.get('sample_count', 0)} samples, "
                f"{primary.get('percentage', 0):.1f}%)"
            )
            primary["confidence"] = compute_confidence(
                primary, static_match=True, graph_evidence=True
            )
            merged.append(primary)

        elif graph_list and not static_list:
            # Only graph DB found it — enrich with source location if possible
            a = graph_list[0]
            a["_dual_evidence"] = False
            a["_approaches"] = ["graph"]
            a["confidence"] = compute_confidence(a, static_match=False, graph_evidence=True)
            merged.append(a)

        elif static_list and not graph_list:
            # Only static analysis found it — lower confidence, mark as static-only
            a = static_list[0]
            a["_dual_evidence"] = False
            a["_approaches"] = ["static"]
            a["confidence"] = compute_confidence(a, static_match=True, graph_evidence=False)
            merged.append(a)

    return merged


def analyze_anomalies(db_path: str, selected_categories: list = None,
                      annotate_non_defects: bool = True,
                      classpath_dir: str = DEFAULT_CLASSPATH_DIR,
                      enable_composite: bool = True,
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

    # Step 1: Run both approaches independently
    graph_anomalies = _run_graph_analyzers(conn, target_keys, reachable_methods, declared_methods)
    static_anomalies = _run_static_patterns(target_keys)

    # Step 2: Build source method index for cross-referencing
    method_index = _build_source_method_index()

    # Step 3: Merge — when both approaches detect the same issue, combine evidence
    if cross_reference:
        all_anomalies = _merge_dual_evidence(static_anomalies, graph_anomalies, method_index)
    else:
        all_anomalies = list(graph_anomalies) + list(static_anomalies)

    # Step 4: Composite cross-cutting detectors (run on merged pool)
    combined = []
    if enable_composite:
        combined = combine_all(
            static_anomalies=static_anomalies,
            graph_anomalies=graph_anomalies,
            diff_entries=None,
            reachable_methods=reachable_methods,
            declared_methods=declared_methods,
        )
        for c in combined:
            c["_approaches"] = ["composite"]
            if "confidence" not in c:
                c["confidence"] = compute_confidence(c, static_match=True, graph_evidence=True)
    all_anomalies.extend(combined)

    # Step 5: Non-defect annotation on non-composite findings
    if annotate_non_defects:
        context = {"growth_status": _build_growth_status(conn)} if annotate_non_defects else None
        non_composite = [a for a in all_anomalies if "composite_sources" not in a]
        composite = [a for a in all_anomalies if "composite_sources" in a]
        annotated = annotate_report_with_non_defects(non_composite, context)
        all_anomalies = annotated + composite

    # Step 6: Ensure every anomaly has confidence
    for a in all_anomalies:
        if "confidence" not in a:
            a["confidence"] = compute_confidence(a)

    # Sort: dual-evidence first, then by confidence desc, then by severity
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_anomalies.sort(key=lambda a: (
        0 if a.get("_dual_evidence") else (1 if a.get("_approaches") == ["graph"] else 2),
        -a.get("confidence", 0),
        severity_rank.get(a.get("severity", "MEDIUM"), 3),
    ))

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
    composite_count = sum(1 for a in defects if "composite_sources" in a)

    prompt = [
        "### AUTOMATED PERFORMANCE ANOMALY REPORT (DUAL-APPROACH: GRAPH DB + STATIC ANALYSIS)",
        f"Analyzed findings: {len(defects)} True Defects | {len(non_defects)} Marked Non-Defects\n",
        f"**Detection Breakdown:**",
        f"- Dual evidence (graph + static): {dual_count}",
        f"- Graph DB only: {graph_only}",
        f"- Static analysis only: {static_only}",
        f"- Cross-cutting composite: {composite_count}\n",
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
                ("composite",): "[COMPOSITE]",
            }.get(tuple(approaches), "")
            dual_tag = " ★ DUAL EVIDENCE" if item.get("_dual_evidence") else ""
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
    prompt.append("1. Prioritize dual-evidence findings (marked ★) — they have both profiling data and source pattern confirmation.")
    prompt.append("2. Graph-only findings have profiling sample counts; investigate the described hot paths.")
    prompt.append("3. Static-only findings are structural patterns found in source; confirm via profiling if possible.")
    prompt.append("4. Provide refactored Java/Spring Boot code snippets resolving true defects.")

    return "\n".join(prompt)


def main():
    parser = argparse.ArgumentParser(description="Orchestrator for KuzuDB taxonomy performance analyzers (T1 - T9)")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KuzuDB database folder")
    parser.add_argument("--category", help="Comma-separated taxonomy IDs to run (e.g., T1,T2,T6). Default runs all.")
    parser.add_argument("--classpath-dir", default=DEFAULT_CLASSPATH_DIR, help="Compiled .class files for T5's static reachability check (default: target/classes)")
    parser.add_argument("--json", action="store_true", help="Output findings as raw JSON")
    parser.add_argument("--prompt-only", action="store_true", help="Output only formatted LLM prompt")
    parser.add_argument("--no-composite", action="store_true", help="Disable composite/cross-cutting detectors")
    parser.add_argument("--no-cross-ref", action="store_true", help="Skip cross-referencing; return separate graph+static lists")

    args = parser.parse_args()

    selected = [c.strip().upper() for c in args.category.split(",")] if args.category else None
    anomalies = analyze_anomalies(args.db_path, selected, classpath_dir=args.classpath_dir,
                                  enable_composite=not args.no_composite,
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
