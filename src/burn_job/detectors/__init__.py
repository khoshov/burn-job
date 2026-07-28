"""Burn-Job Detectors Package."""

from burn_job.detectors.base import BaseDetector
from burn_job.detectors.rule_engine import RuleEngine
from burn_job.detectors.taxonomy import T1RedundantOpsDetector
from burn_job.detectors.composite import combine_all, compute_confidence
from burn_job.detectors._shared import (
    SRC_ROOT,
    REPO_ROOT,
    iter_java_files,
    read_file,
    line_of,
    scan_braces,
    scan_matched,
    strip_comments,
    class_simple_name,
    read_source_window,
    span_end,
    extract_top_level_statements,
    iter_method_bodies,
)

__all__ = [
    "BaseDetector",
    "RuleEngine",
    "T1RedundantOpsDetector",
    "combine_all",
    "compute_confidence",
    "SRC_ROOT",
    "REPO_ROOT",
    "iter_java_files",
    "read_file",
    "line_of",
    "scan_braces",
    "scan_matched",
    "strip_comments",
    "class_simple_name",
    "read_source_window",
    "span_end",
    "extract_top_level_statements",
    "iter_method_bodies",
]
