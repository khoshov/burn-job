"""
Performance anomaly detectors: call graph, complexity, patterns, rule engine,
differential analysis, non-defect classification, and taxonomy analyzers (T1-T9).
"""

from burn_job.detectors.orchestrate import analyze_anomalies, format_llm_prompt
from burn_job.detectors.callgraph import build_static_call_graph, compute_reachable
from burn_job.detectors.patterns import (
    detect_n_plus_one, detect_existence_check_full_fetch,
    detect_nested_loops, detect_duplicate_methods,
)
from burn_job.detectors.object_layout import compute_static_object_layout, compute_layout_for_source_file
from burn_job.detectors.source_mapping import resolve_source_location
from burn_job.detectors.differential import compare_runs, list_run_ids
from burn_job.detectors.non_defects import classify_anomaly_as_non_defect, annotate_report_with_non_defects
from burn_job.detectors.complexity import analyze_complexity
from burn_job.detectors.rule_engine import run
from burn_job.detectors.base import BaseDetector

__all__ = [
    "analyze_anomalies", "format_llm_prompt",
    "build_static_call_graph", "compute_reachable",
    "detect_n_plus_one", "detect_existence_check_full_fetch",
    "detect_nested_loops", "detect_duplicate_methods",
    "compute_static_object_layout", "compute_layout_for_source_file",
    "resolve_source_location",
    "compare_runs", "list_run_ids",
    "classify_anomaly_as_non_defect", "annotate_report_with_non_defects",
    "analyze_complexity",
    "run",
    "BaseDetector",
]
