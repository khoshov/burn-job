#!/usr/bin/env python3
"""
Performance Anomaly Orchestrator for KùzuDB Call Graphs.
Runs modular category analyzers (T1 - T9) to detect performance antipatterns
across CPU, DB, Memory, Concurrency, Algorithms, Data Layout, and Code Structure.
"""

import sys
import os
import argparse
import json

# Add scripts directory to Python path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False

from analyzers.t1_redundant_ops import analyze_t1
from analyzers.t2_inefficient_algos import analyze_t2
from analyzers.t3_improper_func_usage import analyze_t3
from analyzers.t4_data_layout import analyze_t4
from analyzers.t5_redundant_checks import analyze_t5
from analyzers.t6_db_queries import analyze_t6
from analyzers.t7_memory_leak import analyze_t7
from analyzers.t8_memory_bloat import analyze_t8
from analyzers.t9_cpu_hotspots import analyze_t9
from non_defects import annotate_report_with_non_defects


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


def analyze_anomalies(db_path: str, selected_categories: list = None, annotate_non_defects: bool = True) -> list:
    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"Error: KùzuDB database path '{db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    anomalies = []

    target_keys = selected_categories if selected_categories else list(ANALYZER_REGISTRY.keys())
    for key in target_keys:
        key_upper = key.upper()
        if key_upper in ANALYZER_REGISTRY:
            fn = ANALYZER_REGISTRY[key_upper]
            results = fn(conn)
            anomalies.extend(results)

    if annotate_non_defects:
        anomalies = annotate_report_with_non_defects(anomalies)

    return anomalies


def format_llm_prompt(anomalies: list) -> str:
    """Formats detected graph anomalies into a structured prompt for LLM analysis."""
    defects = [a for a in anomalies if a.get("status") != "NON_DEFECT"]
    non_defects = [a for a in anomalies if a.get("status") == "NON_DEFECT"]

    prompt = [
        "### AUTOMATED TAXONOMY ANOMALY DETECTION REPORT (KÙZU GRAPH DB)",
        f"Analyzed findings: {len(defects)} True Defects | {len(non_defects)} Marked Non-Defects (Section 7 Rules)\n"
    ]
    
    if defects:
        prompt.append("#### 🔴 DEFECTS REQUIRING ATTENTION:")
        for idx, item in enumerate(defects, 1):
            prompt.append(f"**Anomaly #{idx}: [{item.get('taxonomy_id', 'TAX')}] {item['type']} [{item['severity']}] (Category: {item['category']})**")
            prompt.append(f"- **Caller:** `{item['caller']}`")
            prompt.append(f"- **Callee:** `{item['callee']}`")
            prompt.append(f"- **Samples / Impact:** {item['sample_count']} samples")
            prompt.append(f"- **Diagnosis:** {item['description']}\n")

    if non_defects:
        prompt.append("#### 🟢 NON-DEFECTS / EXCLUDED BY RULES (SECTION 7):")
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
    parser = argparse.ArgumentParser(description="Orchestrator for KùzuDB taxonomy performance analyzers (T1 - T9)")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder")
    parser.add_argument("--category", help="Comma-separated taxonomy IDs to run (e.g., T1,T2,T6). Default runs all.")
    parser.add_argument("--json", action="store_true", help="Output findings as raw JSON")
    parser.add_argument("--prompt-only", action="store_true", help="Output only formatted LLM prompt")

    args = parser.parse_args()

    selected = [c.strip().upper() for c in args.category.split(",")] if args.category else None
    anomalies = analyze_anomalies(args.db_path, selected)

    if args.json:
        print(json.dumps(anomalies, indent=2))
        return

    llm_prompt = format_llm_prompt(anomalies)

    if args.prompt_only:
        print(llm_prompt)
        return

    print("=========================================================")
    print("   EXPANDED TAXONOMY ANOMALY REPORT (KÙZU GRAPH DB)     ")
    print("=========================================================\n")
    print(llm_prompt)


if __name__ == "__main__":
    main()
