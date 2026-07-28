#!/usr/bin/env python3
"""
Non-Defect Classification Engine (Section 7 Rules)

Implements formal criteria and classification for cases that are NOT considered
performance defects according to project performance standards:

1. FIELD_ORDERING: Class field order in source code (HotSpot reorders fields; JOL verified).
2. BOUNDED_QUADRATIC: Quadratic O(N^2) complexity with contract-bounded input (N <= 8).
3. BOUNDED_CACHE: Cache memory growth up to configured max limit / eviction policy.
4. BOUNDED_REQUEST_COLLECTION: Intermediate collection size limited by validated query parameters.
5. MICROBENCHMARK_NOISE: Micro-optimization costs lost in I/O noise (Pattern.compile, JIT noise).
6. CODE_STYLE: Formatting, line length, method order (zero runtime impact).
7. UNTESTED_COVERAGE_GAP: Code statically reachable from a declared entry point but not exercised
   by the current profiling run (spec 008) — a test-coverage gap, not dead code.

spec 012: each rule now checks real data where it's available (object_layout's static field-layout
calculator for ND-1, a real static @Max/Math.min bound check for ND-2/ND-4, cross-run retained-count
trend for ND-3) instead of re-parsing the description string the anomaly's own analyzer generated a
few lines earlier — that was self-referential and never actually verified anything (see plan/012's
Problem section). Every classification now carries a `confidence` field: "verified" when checked
against real data, "heuristic" when it fell back to the old text match because no real data was
available for that particular anomaly (e.g. only one profiling run in the database, so no cross-run
trend exists yet). ND-6 has no real-data check available at all in this plan and stays "heuristic"
always — see plan/012's non-goal about not attempting a full bytecode diff for that one.
"""

import os
import re
import sys
from typing import Any, Dict, Optional, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


NON_DEFECT_RULES = {
    "ND-1": {
        "id": "NON_DEFECT_FIELD_ORDERING",
        "title": "Порядок объявления полей в классе",
        "description": "HotSpot JVM самостоятельно раскладывает поля по размеру и выравниванию. Порядок в исходнике не влияет на размер объекта (JOL Java 21: 40B vs 40B).",
        "evidence_required": "JOL layout measurement or bytecode analysis showing equal object padding."
    },
    "ND-2": {
        "id": "NON_DEFECT_BOUNDED_QUADRATIC",
        "title": "Квадратичная сложность при ограниченном контрактом входе",
        "description": "Если вход ограничен API (N <= 8 элементов), вложенный цикл O(N^2) выполняется за наносекунды и не вызывает деградацию.",
        "evidence_required": "API contract validation ensuring upper bound N <= 8."
    },
    "ND-3": {
        "id": "NON_DEFECT_BOUNDED_CACHE",
        "title": "Кэш с заданной границей и политикой вытеснения",
        "description": "Рост размера кеша до сконфигурированного лимита (maxSize / Eviction) является проектным поведением, а не утечкой памяти.",
        "evidence_required": "Configured eviction policy (LRU/LFU/Caffeine maxSize) or bounded limit."
    },
    "ND-4": {
        "id": "NON_DEFECT_BOUNDED_REQUEST_COLLECTION",
        "title": "Промежуточная коллекция, ограниченная параметром запроса",
        "description": "Хранение коллекции, максимальный размер которой ограничен валидируемым параметром пагинации/запроса (pageSize <= max).",
        "evidence_required": "Validated request parameter constraint (@Max / Math.min)."
    },
    "ND-5": {
        "id": "NON_DEFECT_MICROBENCHMARK_NOISE",
        "title": "Стоимость, измеримая только в синтетическом микробенчмарке",
        "description": "Микрооптимизации (перекомпиляция Regex, мелкие аллокации), вклад которых в общем времени составляет < 1% и теряется в шуме I/O и БД.",
        "evidence_required": "Profiling sample percentage < 1% or latency dominated by DB network I/O."
    },
    "ND-6": {
        "id": "NON_DEFECT_CODE_STYLE",
        "title": "Стиль кода, не влияющий на поведение и затраты",
        "description": "Перенос скобок, длина строк, порядок методов в файле не изменяют байткод и не имеют накладных расходов.",
        "evidence_required": "Identical compiled bytecode or non-functional structural diff."
    },
    "ND-7": {
        "id": "NON_DEFECT_UNTESTED_COVERAGE_GAP",
        "title": "Код статически достижим, но не покрыт текущим прогоном",
        "description": "Метод достижим от объявленной точки входа (контроллер/main/@Test) по статическому графу вызовов, но не покрыт текущим набором тестов/нагрузочным прогоном. Пробел в покрытии, не мёртвый код.",
        "evidence_required": "Static call-graph reachability from a declared entry point (skill/scripts/static_callgraph.py)."
    }
}


_FILE_LINE_RE = re.compile(r"^(.+\.java):(\d+)$")
_BOUND_ANNOTATION_RE = re.compile(r"@(?:jakarta\.validation\.constraints\.)?Max\s*\(\s*(?:value\s*=\s*)?(\d+)")
_MATH_MIN_RE = re.compile(r"Math\.min\([^,()]+,\s*(\d+)\s*\)")
_BOUND_THRESHOLD = 16  # matches the taxonomy's own "N <= 8"-ish language with a little headroom


def _resolve_any(value: str) -> Optional[Tuple[str, int, int]]:
    """Resolves a caller/callee value to (file, line_from, line_to) — accepts both the Method.id
    convention (via source_mapping) and the "path/File.java:line" convention the spec-009 static
    detectors already produce natively (parsed back out directly, same as export_report.py)."""
    if not value:
        return None
    m = _FILE_LINE_RE.match(value)
    if m:
        line = int(m.group(2))
        return m.group(1), line, line
    try:
        from source_mapping import resolve_source_location
        return resolve_source_location(value)
    except Exception:
        return None


def _read_source_window(file_rel_path: str, line_from: int, before: int = 3, after: int = 2) -> Optional[str]:
    try:
        with open(os.path.join(REPO_ROOT, file_rel_path), "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    start = max(0, line_from - 1 - before)
    end = min(len(lines), line_from + after)
    return "\n".join(lines[start:end])


def _verify_field_ordering(anomaly: Dict[str, Any]) -> Optional[bool]:
    """
    ND-1: for our own WASTED_FIELD_PADDING findings (t4_data_layout.py), recompute the static
    layout via object_layout.compute_static_object_layout and check the real wasted_bytes value —
    True (non-defect) only if it's genuinely 0, False (stays a real defect) if it's genuinely > 0.
    Returns None (fall back to text heuristic) for anything that isn't this specific finding type,
    or if the class can't be located.
    """
    if anomaly.get("type") != "WASTED_FIELD_PADDING":
        return None
    class_fqn = anomaly.get("callee", "")
    try:
        from source_mapping import _class_index
        from object_layout import compute_layout_for_source_file

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
    """
    ND-2/ND-4: looks for a real @Max(N)/Math.min(..., N) bound near the caller's declaration
    instead of trusting the word "bounded" in a generated description. Returns True only if a
    bound small enough to matter (<= _BOUND_THRESHOLD) is actually found in source; False if the
    caller's location resolves but no such bound is present (checked and found nothing — the
    finding stays a real defect, it is NOT silently waved through); None if the caller can't be
    located at all (no static check possible, fall back to the text heuristic).
    """
    anomaly_type = anomaly.get("type", "")
    desc = anomaly.get("description", "").lower()
    is_candidate = anomaly_type in ("QUADRATIC_NESTED_LOOP", "LINEAR_SEARCH_IN_LOOP") or "request" in desc
    if not is_candidate:
        return None

    location = _resolve_any(anomaly.get("caller", ""))
    if location is None:
        return None
    file_path, line_from, _ = location
    window = _read_source_window(file_path, line_from)
    if window is None:
        return None

    m = _BOUND_ANNOTATION_RE.search(window) or _MATH_MIN_RE.search(window)
    if not m:
        return False
    return int(m.group(1)) <= _BOUND_THRESHOLD


def _verify_bounded_cache(anomaly: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[bool]:
    """
    ND-3: uses the real cross-run retained-count trend (differential_analysis.py, spec 011) —
    True (non-defect) if the method's retained count is flat/declining across runs, False (stays a
    real leak finding) if it's genuinely growing, None if no multi-run data exists yet in this
    database (context["growth_status"] wasn't built — falls back to the text heuristic).
    """
    if anomaly.get("type") not in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION"):
        return None
    growth_status = (context or {}).get("growth_status")
    if not growth_status:
        return None
    status = growth_status.get(anomaly.get("callee", ""))
    if status is None:
        return None
    return status != "growing"


def classify_anomaly_as_non_defect(anomaly: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Evaluates an anomaly candidate against Non-Defect rules (Section 7).
    Returns (is_non_defect, rule_meta, confidence) — confidence is "verified" when checked against
    real data, "heuristic" when it fell back to matching the anomaly's own description text
    (no real data was available to check), or None when the anomaly isn't a non-defect at all.
    """
    anomaly_type = anomaly.get("type", "")
    desc = anomaly.get("description", "").lower()
    caller = anomaly.get("caller", "").lower()
    callee = anomaly.get("callee", "").lower()
    pct = anomaly.get("percentage", 0.0)
    samples = anomaly.get("sample_count", 0)

    # Rule 7: Untested-but-reachable code — exact type match, already backed by real
    # static_callgraph.py reachability data at generation time (spec 008).
    if anomaly_type == "UNTESTED_REACHABLE_CODE":
        return True, NON_DEFECT_RULES["ND-7"], "verified"

    # Rule 1: Field Ordering
    verified = _verify_field_ordering(anomaly)
    if verified is True:
        return True, NON_DEFECT_RULES["ND-1"], "verified"
    if verified is False:
        return False, {}, None  # real, confirmed padding waste — must not be waved through
    if "field order" in desc or "padding" in desc or "jol" in desc:
        return True, NON_DEFECT_RULES["ND-1"], "heuristic"

    # Rule 2: Bounded Quadratic Complexity
    if anomaly_type in ("QUADRATIC_NESTED_LOOP", "LINEAR_SEARCH_IN_LOOP"):
        verified = _verify_static_bound(anomaly)
        if verified is True:
            return True, NON_DEFECT_RULES["ND-2"], "verified"
        if verified is False:
            return False, {}, None  # checked the source, no real bound found
        if "bounded" in desc or "n<=8" in desc or "max 8" in desc or "enum" in desc:
            return True, NON_DEFECT_RULES["ND-2"], "heuristic"

    # Rule 3: Bounded Cache / Eviction
    if anomaly_type in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION"):
        verified = _verify_bounded_cache(anomaly, context)
        if verified is True:
            return True, NON_DEFECT_RULES["ND-3"], "verified"
        if verified is False:
            return False, {}, None  # cross-run data shows genuine growth
        if "caffeine" in callee or "guava" in callee or "lru" in desc or "bounded cache" in desc:
            return True, NON_DEFECT_RULES["ND-3"], "heuristic"

    # Rule 4: Bounded Request Collection
    verified = _verify_static_bound(anomaly)
    if verified is True:
        return True, NON_DEFECT_RULES["ND-4"], "verified"
    if verified is False:
        return False, {}, None
    if "request" in desc and ("page" in desc or "limit" in desc or "bounded" in desc):
        return True, NON_DEFECT_RULES["ND-4"], "heuristic"

    # Rule 5: Microbenchmark Noise — targeted check only; the old unconditional
    # `0 < pct < 0.5` catch-all is gone (see plan/012's Problem section: it was swallowing
    # unrelated low-percentage findings of any category for no substantive reason, and the
    # Cypher-level thresholds added in specs 007/011 already gate noise before it gets here).
    if "pattern.compile" in callee or "regex" in desc:
        if pct < 1.0 or samples < 15:
            return True, NON_DEFECT_RULES["ND-5"], "heuristic"

    # Rule 6: Code Style — no real-data check exists for this in the current plan; always heuristic.
    if "style" in desc or "formatting" in desc or "brace" in desc:
        return True, NON_DEFECT_RULES["ND-6"], "heuristic"

    return False, {}, None


def annotate_report_with_non_defects(anomalies: list, context: Optional[Dict[str, Any]] = None) -> list:
    """
    Annotates anomaly list with is_defect flag and non_defect_reason if applicable. `context`
    (spec 012) carries real data other than the anomaly dict itself — currently just
    context["growth_status"]: Dict[method_id, "growing"|"stable"|"declining"], built from
    differential_analysis.compare_runs() when the database holds 2+ profiling runs.
    """
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
