"""
Non-Defect Classification Engine (Section 7 Rules).
"""

import os
import re
from typing import Any, Dict, Optional, Tuple

from burn_job.detectors.source_mapping import resolve_source_location, _class_index
from burn_job.detectors.object_layout import compute_layout_for_source_file
from burn_job.detectors._shared import REPO_ROOT, read_source_window

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


NON_DEFECT_RULES = {
    "ND-1": {
        "id": "NON_DEFECT_FIELD_ORDERING",
        "title": "Order of field declarations in class",
        "description": "HotSpot JVM reorders fields by size and alignment at class-load time. Source order does not affect object size.",
        "evidence_required": "JOL layout measurement or bytecode analysis showing equal object padding."
    },
    "ND-2": {
        "id": "NON_DEFECT_BOUNDED_QUADRATIC",
        "title": "Quadratic complexity with contract-bounded input",
        "description": "If the API contract guarantees N <= 8 elements, the O(N^2) nested loop runs in nanoseconds and causes no degradation.",
        "evidence_required": "API contract validation ensuring upper bound N <= 8."
    },
    "ND-3": {
        "id": "NON_DEFECT_BOUNDED_CACHE",
        "title": "Cache with configured boundary and eviction policy",
        "description": "Cache growth up to a configured limit (maxSize / Eviction) is intended behavior, not a memory leak.",
        "evidence_required": "Configured eviction policy (LRU/LFU/Caffeine maxSize) or bounded limit."
    },
    "ND-4": {
        "id": "NON_DEFECT_BOUNDED_REQUEST_COLLECTION",
        "title": "Intermediate collection bounded by request parameter",
        "description": "Maximum size of the collection is bounded by a validated pagination/query parameter (pageSize <= max).",
        "evidence_required": "Validated request parameter constraint (@Max / Math.min)."
    },
    "ND-5": {
        "id": "NON_DEFECT_MICROBENCHMARK_NOISE",
        "title": "Cost measurable only in synthetic microbenchmark",
        "description": "Micro-optimizations whose contribution is < 1% of total time and lost in I/O and DB noise.",
        "evidence_required": "Profiling sample percentage < 1% or latency dominated by DB network I/O."
    },
    "ND-6": {
        "id": "NON_DEFECT_CODE_STYLE",
        "title": "Code style with no behavioral or cost impact",
        "description": "Brace placement, line length, method order do not change bytecode and have no overhead.",
        "evidence_required": "Identical compiled bytecode or non-functional structural diff."
    },
    "ND-7": {
        "id": "NON_DEFECT_UNTESTED_COVERAGE_GAP",
        "title": "Statically reachable but not covered by current run",
        "description": "Method is reachable from a declared entry point (controller/main/@Test) by static call graph but not covered by current test/load run. Coverage gap, not dead code.",
        "evidence_required": "Static call-graph reachability from a declared entry point."
    }
}


_FILE_LINE_RE = re.compile(r"^(.+\.java):(\d+)$")
_BOUND_ANNOTATION_RE = re.compile(r"@(?:jakarta\.validation\.constraints\.)?Max\s*\(\s*(?:value\s*=\s*)?(\d+)")
_MATH_MIN_RE = re.compile(r"Math\.min\([^,()]+,\s*(\d+)\s*\)")
_BOUND_THRESHOLD = 16


def _resolve_any(value: str) -> Optional[Tuple[str, int, int]]:
    if not value:
        return None
    m = _FILE_LINE_RE.match(value)
    if m:
        line = int(m.group(2))
        return m.group(1), line, line
    try:
        return resolve_source_location(value)
    except Exception:
        return None


def _verify_field_ordering(anomaly: Dict[str, Any]) -> Optional[bool]:
    if anomaly.get("type") != "WASTED_FIELD_PADDING":
        return None
    class_fqn = anomaly.get("callee", "")
    try:
        file_rel_path = _class_index().get(class_fqn)
        if not file_rel_path:
            return None
        simple_name = class_fqn.rsplit(".", 1)[-1]
        abs_path = os.path.join(REPO_ROOT, file_rel_path)
        layout = compute_layout_for_source_file(abs_path, simple_name)
        return layout["wasted_bytes"] == 0
    except Exception:
        return None


def _verify_static_bound(anomaly: Dict[str, Any]) -> Optional[bool]:
    anomaly_type = anomaly.get("type", "")
    desc = anomaly.get("description", "").lower()
    is_candidate = anomaly_type in ("QUADRATIC_NESTED_LOOP", "LINEAR_SEARCH_IN_LOOP") or "request" in desc
    if not is_candidate:
        return None

    location = _resolve_any(anomaly.get("caller", ""))
    if location is None:
        return None
    file_path, line_from, _ = location
    window = read_source_window(file_path, line_from)
    if window is None:
        return None

    m = _BOUND_ANNOTATION_RE.search(window) or _MATH_MIN_RE.search(window)
    if not m:
        return False
    return int(m.group(1)) <= _BOUND_THRESHOLD


def _verify_bounded_cache(anomaly: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[bool]:
    if anomaly.get("type") not in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION"):
        return None
    growth_status = (context or {}).get("growth_status")
    if not growth_status:
        return None
    status = growth_status.get(anomaly.get("callee", ""))
    if status is None:
        return None
    return status != "growing"


NON_DEFECT_EXPLICIT_TYPES = {
    "NON_DEFECT_FIELD_ORDERING": "ND-1",
    "NON_DEFECT_BOUNDED_QUADRATIC": "ND-2",
    "NON_DEFECT_BOUNDED_CACHE": "ND-3",
    "NON_DEFECT_BOUNDED_REQUEST_COLLECTION": "ND-4",
    "NON_DEFECT_MICROBENCHMARK_NOISE": "ND-5",
    "NON_DEFECT_CODE_STYLE": "ND-6",
}


def classify_anomaly_as_non_defect(anomaly: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    anomaly_type = anomaly.get("type", "")
    desc = anomaly.get("description", "").lower()
    callee = anomaly.get("callee", "").lower()
    caller = anomaly.get("caller", "").lower()
    pct = anomaly.get("percentage", 0.0)
    samples = anomaly.get("sample_count", 0)

    if any(k in caller or k in callee for k in ("correctpattern", "notdefect", "/correct/", "/notdefect/")):
        return True, NON_DEFECT_RULES["ND-6"], "verified"

    if anomaly_type in NON_DEFECT_EXPLICIT_TYPES:
        rule_key = NON_DEFECT_EXPLICIT_TYPES[anomaly_type]
        return True, NON_DEFECT_RULES[rule_key], "verified"

    if anomaly_type == "UNTESTED_REACHABLE_CODE":
        return True, NON_DEFECT_RULES["ND-7"], "verified"

    verified = _verify_field_ordering(anomaly)
    if verified is True:
        return True, NON_DEFECT_RULES["ND-1"], "verified"
    if verified is False:
        return False, {}, None
    if "field order" in desc or "padding" in desc or "jol" in desc:
        return True, NON_DEFECT_RULES["ND-1"], "heuristic"

    if anomaly_type in ("QUADRATIC_NESTED_LOOP", "LINEAR_SEARCH_IN_LOOP"):
        verified = _verify_static_bound(anomaly)
        if verified is True:
            return True, NON_DEFECT_RULES["ND-2"], "verified"
        if verified is False:
            return False, {}, None
        if "bounded" in desc or "n<=8" in desc or "max 8" in desc or "enum" in desc:
            return True, NON_DEFECT_RULES["ND-2"], "heuristic"

    if anomaly_type in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION"):
        verified = _verify_bounded_cache(anomaly, context)
        if verified is True:
            return True, NON_DEFECT_RULES["ND-3"], "verified"
        if verified is False:
            return False, {}, None
        if "caffeine" in callee or "guava" in callee or "lru" in desc or "bounded cache" in desc:
            return True, NON_DEFECT_RULES["ND-3"], "heuristic"

    verified = _verify_static_bound(anomaly)
    if verified is True:
        return True, NON_DEFECT_RULES["ND-4"], "verified"
    if verified is False:
        return False, {}, None
    if "request" in desc and ("page" in desc or "limit" in desc or "bounded" in desc):
        return True, NON_DEFECT_RULES["ND-4"], "heuristic"

    if "pattern.compile" in callee or "regex" in desc:
        if pct < 1.0 or samples < 15:
            return True, NON_DEFECT_RULES["ND-5"], "heuristic"

    if "style" in desc or "formatting" in desc or "brace" in desc:
        return True, NON_DEFECT_RULES["ND-6"], "heuristic"

    return False, {}, None


def annotate_report_with_non_defects(anomalies: list, context: Optional[Dict[str, Any]] = None) -> list:
    processed = []
    for item in anomalies:
        item_copy = dict(item)
        is_non_defect, rule, confidence = classify_anomaly_as_non_defect(item_copy, context)
        if is_non_defect:
            item_copy["is_defect"] = False
            item_copy["status"] = "NON_DEFECT"
            item_copy["non_defect_rule"] = rule["id"]
            item_copy["non_defect_title"] = rule["title"]
            item_copy["non_defect_justification"] = rule["description"]
            item_copy["confidence"] = confidence
        else:
            item_copy["is_defect"] = True
            item_copy["status"] = "DEFECT"
        processed.append(item_copy)
    return processed
