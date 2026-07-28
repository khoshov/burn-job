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
"""

import re
from typing import Dict, Any, Tuple


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
    }
}


def classify_anomaly_as_non_defect(anomaly: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates an anomaly candidate against Non-Defect rules (Section 7).
    Returns (is_non_defect: bool, rule_meta: Dict).
    """
    category = anomaly.get("category", "")
    anomaly_type = anomaly.get("type", "")
    desc = anomaly.get("description", "").lower()
    caller = anomaly.get("caller", "").lower()
    callee = anomaly.get("callee", "").lower()
    pct = anomaly.get("percentage", 0.0)
    samples = anomaly.get("sample_count", 0)

    # Rule 1: Field Ordering
    if "field order" in desc or "padding" in desc or "jol" in desc:
        return True, NON_DEFECT_RULES["ND-1"]

    # Rule 2: Bounded Quadratic Complexity
    if anomaly_type in ("QUADRATIC_NESTED_LOOP", "LINEAR_SEARCH_IN_LOOP") or "o(n^2)" in desc:
        if "bounded" in desc or "n<=8" in desc or "max 8" in desc or "enum" in desc:
            return True, NON_DEFECT_RULES["ND-2"]

    # Rule 3: Bounded Cache / Eviction
    if anomaly_type in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION"):
        if "caffeine" in callee or "guava" in callee or "lru" in desc or "bounded cache" in desc:
            return True, NON_DEFECT_RULES["ND-3"]

    # Rule 4: Bounded Request Collection
    if "request" in desc and ("page" in desc or "limit" in desc or "bounded" in desc):
        return True, NON_DEFECT_RULES["ND-4"]

    # Rule 5: Microbenchmark Noise
    if "pattern.compile" in callee or "regex" in desc:
        if pct < 1.0 or samples < 15:
            return True, NON_DEFECT_RULES["ND-5"]
    if pct > 0 and pct < 0.5:
        return True, NON_DEFECT_RULES["ND-5"]

    # Rule 6: Code Style
    if "style" in desc or "formatting" in desc or "brace" in desc:
        return True, NON_DEFECT_RULES["ND-6"]

    return False, {}


def annotate_report_with_non_defects(anomalies: list) -> list:
    """
    Annotates anomaly list with is_defect flag and non_defect_reason if applicable.
    """
    processed = []
    for item in anomalies:
        item_copy = dict(item)
        is_non_defect, rule = classify_anomaly_as_non_defect(item_copy)
        if is_non_defect:
            item_copy["is_defect"] = False
            item_copy["status"] = "NON_DEFECT"
            item_copy["non_defect_rule"] = rule["id"]
            item_copy["non_defect_title"] = rule["title"]
            item_copy["non_defect_justification"] = rule["description"]
        else:
            item_copy["is_defect"] = True
            item_copy["status"] = "DEFECT"
        processed.append(item_copy)
    return processed
