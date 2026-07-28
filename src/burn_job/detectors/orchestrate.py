"""
Performance Anomaly Orchestrator for KuzuDB Call Graphs.
Runs modular category analyzers (T1 - T9) to detect performance antipatterns
across CPU, DB, Memory, Concurrency, Algorithms, Data Layout, and Code Structure.
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


def analyze_anomalies(db_path: str, selected_categories: list = None, annotate_non_defects: bool = True, classpath_dir: str = DEFAULT_CLASSPATH_DIR) -> list:
    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"Error: KuzuDB database path '{db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    anomalies = []

    target_keys = selected_categories if selected_categories else list(ANALYZER_REGISTRY.keys())

    reachable_methods = declared_methods = None
    if "T5" in [k.upper() for k in target_keys] and classpath_dir and os.path.isdir(classpath_dir):
        call_graph, entry_points = build_static_call_graph(classpath_dir)
        declared_methods = set(call_graph.keys())
        reachable_methods = compute_reachable(call_graph, entry_points)

    for key in target_keys:
        key_upper = key.upper()
        if key_upper not in ANALYZER_REGISTRY:
            continue
        fn = ANALYZER_REGISTRY[key_upper]
        if key_upper == "T5":
            results = fn(conn, reachable_methods=reachable_methods, declared_methods=declared_methods)
        else:
            results = fn(conn)
        anomalies.extend(results)

    for key in target_keys:
        key_upper = key.upper()
        if key_upper in STATIC_PATTERN_DETECTORS:
            anomalies.extend(STATIC_PATTERN_DETECTORS[key_upper]())

    if annotate_non_defects:
        context = {"growth_status": _build_growth_status(conn)} if annotate_non_defects else None
        anomalies = annotate_report_with_non_defects(anomalies, context)

    return anomalies


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

    prompt = [
        "### AUTOMATED TAXONOMY ANOMALY DETECTION REPORT (KUZU GRAPH DB)",
        f"Analyzed findings: {len(defects)} True Defects | {len(non_defects)} Marked Non-Defects (Section 7 Rules)\n"
    ]

    if defects:
        prompt.append("#### DEFECTS REQUIRING ATTENTION:")
        for idx, item in enumerate(defects, 1):
            prompt.append(f"**Anomaly #{idx}: [{item.get('taxonomy_id', 'TAX')}] {item['type']} [{item['severity']}] (Category: {item['category']})**")
            prompt.append(f"- **Caller:** `{item['caller']}`")
            prompt.append(f"- **Callee:** `{item['callee']}`")
            prompt.append(f"- **Samples / Impact:** {item['sample_count']} samples")
            prompt.append(f"- **Diagnosis:** {item['description']}\n")

    if non_defects:
        prompt.append("#### NON-DEFECTS / EXCLUDED BY RULES (SECTION 7):")
        for idx, item in enumerate(non_defects, 1):
            prompt.append(f"**Item #{idx}: [{item.get('non_defect_rule')}] {item.get('non_defect_title')}**")
            prompt.append(f"- **Candidate Method:** `{item['caller']}` -> `{item['callee']}`")
            prompt.append(f"- **Reason:** {item.get('non_defect_justification')}\n")

    prompt.append("### INSTRUCTIONS FOR LLM:")
    prompt.append("1. Provide a detailed technical explanation for each true defect.")
    prompt.append("2. Confirm non-defect status for items marked in Section 7 without requesting code refactoring.")
    prompt.append("3. Provide refactored Java/Spring Boot code snippets resolving true defects.")

    return "\n".join(prompt)


def main():
    parser = argparse.ArgumentParser(description="Orchestrator for KuzuDB taxonomy performance analyzers (T1 - T9)")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KuzuDB database folder")
    parser.add_argument("--category", help="Comma-separated taxonomy IDs to run (e.g., T1,T2,T6). Default runs all.")
    parser.add_argument("--classpath-dir", default=DEFAULT_CLASSPATH_DIR, help="Compiled .class files for T5's static reachability check (default: target/classes)")
    parser.add_argument("--json", action="store_true", help="Output findings as raw JSON")
    parser.add_argument("--prompt-only", action="store_true", help="Output only formatted LLM prompt")

    args = parser.parse_args()

    selected = [c.strip().upper() for c in args.category.split(",")] if args.category else None
    anomalies = analyze_anomalies(args.db_path, selected, classpath_dir=args.classpath_dir)

    if args.json:
        print(json.dumps(anomalies, indent=2))
        return

    llm_prompt = format_llm_prompt(anomalies)

    if args.prompt_only:
        print(llm_prompt)
        return

    print("=========================================================")
    print("   EXPANDED TAXONOMY ANOMALY REPORT (KUZU GRAPH DB)     ")
    print("=========================================================\n")
    print(llm_prompt)


if __name__ == "__main__":
    main()
