"""detection subpackage."""

from static_pattern_detectors import (
    detect_n_plus_one,
    detect_existence_check_full_fetch,
    detect_nested_loops,
    detect_duplicate_methods,
)
from detection.base import BaseDetector, SRC_ROOT, _iter_java_files, _read, _line_of, _scan_braces

__all__ = [
    "detect_n_plus_one",
    "detect_existence_check_full_fetch",
    "detect_nested_loops",
    "detect_duplicate_methods",
    "BaseDetector",
]
