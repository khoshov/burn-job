"""
Composite / cross-cutting detectors and confidence scoring.

Combines signals from multiple taxonomy categories to produce
higher-confidence, more specific findings.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


def compute_confidence(anomaly: dict, static_match: bool = False, graph_evidence: bool = False,
                       cross_run_diff: Optional[dict] = None) -> float:
    evidence_count = 0
    evidence_count += 1 if static_match else 0
    evidence_count += 1 if graph_evidence else 0
    evidence_count += 1 if cross_run_diff else 0

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
    if anomaly.get("status") == "NON_DEFECT":
        base = min(base + 0.05, 0.95)

    return round(base, 2)


def _method_key(anomaly: dict) -> str:
    return f"{anomaly.get('caller', '')} -> {anomaly.get('callee', '')}"


def combine_n_plus_one_with_nested_loops(static_anomalies: List[dict],
                                          graph_anomalies: List[dict]) -> List[dict]:
    n_plus_one = {_method_key(a): a for a in static_anomalies if a.get("type") == "N_PLUS_ONE_QUERIES"
                  or _method_key(a) in {_method_key(g) for g in graph_anomalies
                                        if g.get("type") == "N_PLUS_ONE_QUERIES"}}
    nested_loops = {_method_key(a): a for a in static_anomalies if a.get("type") == "QUADRATIC_NESTED_LOOP"}

    combined = []
    seen_keys = set()

    for loop_key, loop_anomaly in nested_loops.items():
        for n1_key, n1_anomaly in n_plus_one.items():
            loop_caller = loop_anomaly.get("callee", "")
            n1_caller = n1_anomaly.get("caller", "")
            if loop_caller and n1_caller and loop_caller == n1_caller:
                result_key = f"COMPOSITE_NP1_NESTED:{n1_key}"
                if result_key not in seen_keys:
                    seen_keys.add(result_key)
                    combined.append({
                        "taxonomy_id": "T6",
                        "category": "DATABASE_QUERIES",
                        "type": "N_PLUS_ONE_INSIDE_NESTED_LOOP",
                        "severity": "CRITICAL",
                        "caller": loop_anomaly.get("callee", ""),
                        "callee": n1_anomaly.get("callee", ""),
                        "sample_count": n1_anomaly.get("sample_count", 0) + loop_anomaly.get("sample_count", 0),
                        "percentage": n1_anomaly.get("percentage", 0) + loop_anomaly.get("percentage", 0),
                        "description": (
                            f"N+1 query pattern detected inside a nested loop in method "
                            f"'{loop_anomaly.get('callee', '')}'. This causes O(N*M) database queries "
                            f"where M = lazy collection accesses per outer iteration. "
                            f"Use JOIN FETCH and batch the outer loop."
                        ),
                        "confidence": compute_confidence(n1_anomaly, static_match=True, graph_evidence=True),
                        "composite_sources": [n1_key, loop_key],
                    })

    return combined


def combine_cpu_hotspots_with_memory_growth(graph_anomalies: List[dict],
                                             diff_entries: Optional[List[dict]] = None) -> List[dict]:
    cpu_hotspots = {a.get("callee", ""): a for a in graph_anomalies if a.get("type") == "CPU_HOTSPOT_METHOD"}
    mem_growth = {a.get("callee", ""): a for a in graph_anomalies
                  if a.get("type") in ("UNBOUNDED_CACHE_OR_COLLECTION_GROWTH", "RETAINED_OBJECT_ACCUMULATION")}

    diff_by_method: Dict[str, dict] = {}
    if diff_entries:
        for d in diff_entries:
            if d.get("metric") in ("Allocation.bytes", "RetainedObject.count"):
                diff_by_method[d["method"]] = d

    combined = []
    seen = set()
    for method in set(cpu_hotspots) & set(mem_growth):
        if method not in seen:
            seen.add(method)
            cpu = cpu_hotspots[method]
            mem = mem_growth[method]
            diff = diff_by_method.get(method)

            combined.append({
                "taxonomy_id": "T9",
                "category": "CPU_LOAD",
                "type": "HOTSPOT_WITH_MEMORY_GROWTH",
                "severity": "CRITICAL",
                "caller": cpu.get("caller", ""),
                "callee": method,
                "sample_count": cpu.get("sample_count", 0) + mem.get("sample_count", 0),
                "percentage": cpu.get("percentage", 0),
                "description": (
                    f"Method '{method}' is both a CPU hotspot and shows memory growth. "
                    f"High CPU may be caused by GC pressure from allocation/memory leak. "
                    f"Profile allocation sites in this method and cache results."
                ),
                "confidence": compute_confidence(cpu, graph_evidence=True,
                                                  cross_run_diff=diff),
                "composite_sources": ["CPU_HOTSPOT_METHOD", mem.get("type", "")],
            })

    return combined


def combine_dead_code_with_test_coverage(graph_anomalies: List[dict],
                                          reachable_methods: Optional[Set[str]] = None,
                                          declared_methods: Optional[Set[str]] = None) -> List[dict]:
    dead_code = [a for a in graph_anomalies if a.get("type") == "DEAD_OR_UNREACHABLE_CODE"]

    combined = []
    for anomaly in dead_code:
        callee = anomaly.get("callee", "")
        if callee and reachable_methods is not None and declared_methods is not None:
            normalized = callee.replace("/", ".")
            has_entry_point = normalized in reachable_methods if reachable_methods else False
            if not has_entry_point and normalized in declared_methods:
                combined.append({
                    "taxonomy_id": "T5",
                    "category": "REDUNDANT_OPERATIONS",
                    "type": "DEAD_CODE_WITH_COVERAGE_GAP",
                    "severity": "MEDIUM",
                    "caller": anomaly.get("caller", ""),
                    "callee": callee,
                    "sample_count": 0,
                    "percentage": 0.0,
                    "description": (
                        f"Method '{callee}' is unreachable from any entry point "
                        f"(controller, @Test, main). This is dead code with no test coverage. "
                        f"Remove or add an entry point if still needed."
                    ),
                    "confidence": 0.9,
                    "composite_sources": ["DEAD_OR_UNREACHABLE_CODE"],
                })

    return combined


def combine_existence_check_with_full_fetch(graph_anomalies: List[dict],
                                             static_anomalies: List[dict]) -> List[dict]:
    existence_checks = {_method_key(a): a for a in graph_anomalies
                        if a.get("type") == "FULL_FETCH_FOR_EXISTENCE_CHECK"}
    heavy_fetches = {_method_key(a): a for a in graph_anomalies
                     if a.get("type") == "HEAVY_ENTITY_FETCH"}

    combined = []
    seen = set()
    for key, existence in existence_checks.items():
        heavy = heavy_fetches.get(key)
        if heavy:
            result_key = f"COMPOSITE_EXISTENCE_HEAVY:{key}"
            if result_key not in seen:
                seen.add(result_key)
                combined.append({
                    "taxonomy_id": "T3",
                    "category": "MEMORY_BLOAT",
                    "type": "FULL_FETCH_WITH_HEAVY_PAYLOAD",
                    "severity": "HIGH",
                    "caller": existence.get("caller", ""),
                    "callee": existence.get("callee", ""),
                    "sample_count": existence.get("sample_count", 0) + heavy.get("sample_count", 0),
                    "percentage": existence.get("percentage", 0),
                    "description": (
                        f"Full entity fetch in '{existence.get('caller', '')}' for existence check, "
                        f"combined with heavy ORM payload conversion. "
                        f"Replace with existsBy...() COUNT query and DTO projection."
                    ),
                    "confidence": compute_confidence(existence, static_match=True, graph_evidence=True),
                    "composite_sources": ["FULL_FETCH_FOR_EXISTENCE_CHECK", "HEAVY_ENTITY_FETCH"],
                })

    return combined


def combine_all(static_anomalies: List[dict],
                graph_anomalies: List[dict],
                diff_entries: Optional[List[dict]] = None,
                reachable_methods: Optional[Set[str]] = None,
                declared_methods: Optional[Set[str]] = None) -> List[dict]:
    result = []
    result.extend(combine_n_plus_one_with_nested_loops(static_anomalies, graph_anomalies))
    result.extend(combine_cpu_hotspots_with_memory_growth(graph_anomalies, diff_entries))
    result.extend(combine_dead_code_with_test_coverage(graph_anomalies, reachable_methods, declared_methods))
    result.extend(combine_existence_check_with_full_fetch(graph_anomalies, diff_entries))

    for a in result:
        if "confidence" not in a:
            a["confidence"] = compute_confidence(a)

    return result
