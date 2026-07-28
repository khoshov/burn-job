"""Generic engine and registry for defect detectors and graph_rules.yaml."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from burn_job.core.protocols import DetectorProtocol
from burn_job.domain.finding import Finding
from burn_job.domain.pipeline_context import PipelineContext

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(_THIS_DIR, "..", "resources", "rules", "graph_rules.yaml")


RULE_FIELD_MAP = {
    "caller_class_contains": ("a", "className", "CONTAINS"),
    "caller_class_equals": ("a", "className", "="),
    "caller_method_contains": ("a", "methodName", "CONTAINS"),
    "caller_method_equals": ("a", "methodName", "="),
    "callee_class_contains": ("b", "className", "CONTAINS"),
    "callee_class_equals": ("b", "className", "="),
    "callee_method_contains": ("b", "methodName", "CONTAINS"),
    "callee_method_equals": ("b", "methodName", "="),
    "class_contains": ("m", "className", "CONTAINS"),
    "class_equals": ("m", "className", "="),
    "class_starts_with": ("m", "className", "STARTS WITH"),
}


def _build_condition_clauses(match_block: dict, node_alias: str = "a") -> Tuple[List[str], List[str]]:
    clauses = []
    params = []
    if not match_block:
        return clauses, params

    for field, values in match_block.items():
        if field == "any":
            or_groups = []
            for group in values:
                inner_clauses, inner_params = _build_condition_clauses(group, node_alias)
                or_groups.append("(" + " AND ".join(inner_clauses) + ")")
                params.extend(inner_params)
            if or_groups:
                clauses.append("(" + " OR ".join(or_groups) + ")")
            continue

        if field not in RULE_FIELD_MAP:
            continue
        prefix, col, op = RULE_FIELD_MAP[field]
        if not isinstance(values, list):
            values = [values]
        for val in values:
            param_name = f"p{len(params)}"
            if op == "CONTAINS":
                clauses.append(f"{prefix}.{col} CONTAINS ${param_name}")
            elif op == "STARTS WITH":
                clauses.append(f"{prefix}.{col} STARTS WITH ${param_name}")
            elif op == "=":
                clauses.append(f"{prefix}.{col} = ${param_name}")
            params.append(val)

    return clauses, params


def _execute_edge_rule(conn, rule: dict) -> List[dict]:
    match_clauses, match_params = _build_condition_clauses(rule.get("match"), "a")
    exclude_clauses, exclude_params = _build_condition_clauses(rule.get("exclude"), "a")
    threshold = rule.get("threshold", {})
    order_by = rule.get("order_by", {})
    limit = rule.get("limit")

    cypher_parts = [
        "MATCH ()-[all_r:CALLS]->()",
        "WITH sum(all_r.count) AS totalSamples",
        "MATCH (a:Method)-[r:CALLS]->(b:Method)",
    ]

    where_parts = []
    if match_clauses:
        where_parts.extend(match_clauses)
    if exclude_clauses:
        where_parts.append("NOT (" + " AND ".join(exclude_clauses) + ")")
    if where_parts:
        cypher_parts.append("WHERE " + " AND ".join(where_parts))

    cypher_parts.append(
        "RETURN a.className + '.' + a.methodName AS caller, "
        "b.className + '.' + b.methodName AS callee, "
        "r.count AS count, "
        "cast(r.count AS DOUBLE) / cast(totalSamples AS DOUBLE) * 100.0 AS percent"
    )

    if order_by:
        direction = order_by.get("direction", "DESC")
        field_map = {"sampleCount": "r.count", "count": "r.count", "percent": "percent"}
        cypher_parts.append(f"ORDER BY {field_map.get(order_by['field'], 'r.count')} {direction}")

    if limit:
        cypher_parts.append(f"LIMIT {limit}")

    query = "\n".join(cypher_parts)
    all_params = {**match_params, **exclude_params}

    try:
        res = conn.execute(query, all_params)
    except Exception:
        return []

    anomalies = []
    total_count = 0
    while res.has_next():
        caller, callee, count, percent = res.get_next()
        total_count = max(total_count, count or 0)

        if threshold:
            field = threshold.get("field", "percent")
            op = threshold.get("op", ">")
            val = threshold.get("value", 0)
            actual = percent if field == "percent" else (count or 0)
            if op == ">" and not (actual > val):
                continue
            elif op == ">=" and not (actual >= val):
                continue
            elif op == "<" and not (actual < val):
                continue
            elif op == "<=" and not (actual <= val):
                continue

        sample_count = count or 0
        pct = round(percent, 2) if percent is not None else 0.0

        description = rule.get("description_template", "").format(
            caller=caller, callee=callee,
            count=sample_count, pct=pct
        )

        severity = rule.get("severity", "MEDIUM")
        sev_override = rule.get("severity_override")
        if sev_override:
            if sev_override.get("low_if_percent_lte") is not None and pct <= sev_override["low_if_percent_lte"]:
                severity = "LOW"
            elif sev_override.get("low_if_caller_contains"):
                for pat in sev_override["low_if_caller_contains"]:
                    if pat in caller:
                        severity = "LOW"
                        break

        anomalies.append({
            "taxonomy_id": rule.get("primary_taxonomy", "TAX"),
            "category": rule.get("category", ""),
            "type": rule["id"],
            "severity": severity,
            "caller": caller,
            "callee": callee,
            "sample_count": sample_count,
            "percentage": pct,
            "description": description,
        })

    return anomalies


def _execute_node_rule(conn, rule: dict) -> List[dict]:
    match_clauses, match_params = _build_condition_clauses(rule.get("match"), "m")
    threshold = rule.get("threshold", {})
    order_by = rule.get("order_by", {})
    limit = rule.get("limit")

    caller_label = rule.get("caller_label", "")

    cypher_parts = [
        "MATCH (m:Method)",
    ]

    if match_clauses:
        cypher_parts.append("WHERE " + " AND ".join(match_clauses))

    cypher_parts.append(
        "RETURN m.className + '.' + m.methodName AS callee"
    )

    if order_by:
        direction = order_by.get("direction", "DESC")
        cypher_parts.append(f"ORDER BY 1 {direction}")

    if limit:
        cypher_parts.append(f"LIMIT {limit}")

    query = "\n".join(cypher_parts)

    try:
        total_res = conn.execute("MATCH (m:Method) RETURN count(m) AS c")
        total_count = 0
        if total_res.has_next():
            total_count = total_res.get_next()[0] or 1

        res = conn.execute(query, match_params)
    except Exception:
        return []

    anomalies = []
    while res.has_next():
        callee = res.get_next()[0]

        sample_count = 0
        pct = 0.0

        if threshold:
            op = threshold.get("op", ">")
            val = threshold.get("value", 0)
            if op == ">" and not (pct > val):
                continue

        description = rule.get("description_template", "").format(
            caller=caller_label, callee=callee,
            count=sample_count, pct=pct
        )

        anomalies.append({
            "taxonomy_id": rule.get("primary_taxonomy", "TAX"),
            "category": rule.get("category", ""),
            "type": rule["id"],
            "severity": rule.get("severity", "MEDIUM"),
            "caller": caller_label or callee,
            "callee": callee,
            "sample_count": sample_count,
            "percentage": pct,
            "description": description,
        })

    return anomalies


class RuleEngine:
    """Registry and orchestrator for defect detectors."""

    def __init__(self) -> None:
        self._detectors: List[DetectorProtocol] = []

    def register(self, detector: DetectorProtocol) -> None:
        """Register a detector instance complying with DetectorProtocol."""
        if isinstance(detector, DetectorProtocol):
            self._detectors.append(detector)

    def get_registered_detectors(self) -> Tuple[DetectorProtocol, ...]:
        """Return tuple of registered detectors."""
        return tuple(self._detectors)

    def run_all(self, context: PipelineContext) -> Tuple[Finding, ...]:
        """Execute all registered detectors across the pipeline context."""
        findings = []
        for detector in self._detectors:
            results = detector.analyze(context)
            findings.extend(results)
        return tuple(findings)


def _load_rules(filter_taxonomy: Optional[str] = None) -> List[Dict[str, Any]]:
    if not HAS_YAML or not os.path.exists(RULES_PATH):
        return []
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", [])
    if filter_taxonomy:
        rules = [
            r for r in rules
            if r.get("primary_taxonomy") == filter_taxonomy
            or filter_taxonomy in r.get("also_relevant_to", [])
        ]
    return rules


def run(conn, taxonomy: str) -> List[dict]:
    if not HAS_YAML:
        return []

    rules = _load_rules(taxonomy)
    if not rules:
        return []

    anomalies = []
    for rule in rules:
        if "edge" in rule:
            anomalies.extend(_execute_edge_rule(conn, rule))
        elif "node_type" in rule:
            anomalies.extend(_execute_node_rule(conn, rule))

    return anomalies
