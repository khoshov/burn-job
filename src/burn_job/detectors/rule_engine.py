"""
Generic engine for the data-driven rules in resources/rules/graph_rules.yaml.
"""

import os
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(_THIS_DIR, "..", "resources", "rules", "graph_rules.yaml")

_OP_TO_CYPHER = {"contains": "CONTAINS", "equals": "=", "starts_with": "STARTS WITH"}
_FIELD_TO_COLUMN = {
    "caller_class": "a.className",
    "caller_method": "a.methodName",
    "callee_class": "b.className",
    "callee_method": "b.methodName",
    "class": "m.className",
}
_THRESHOLD_OPS = {
    ">": lambda v, t: v > t,
    ">=": lambda v, t: v >= t,
    "<": lambda v, t: v < t,
    "<=": lambda v, t: v <= t,
    "==": lambda v, t: v == t,
}


def _load_rules() -> List[Dict[str, Any]]:
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])


def _quote(value: str) -> str:
    return "'" + str(value).replace("'", "\\'") + "'"


def _build_single_group(group: Dict[str, Any]) -> str:
    clauses = []
    for key, values in group.items():
        if key == "any":
            continue
        for op_name, cypher_op in _OP_TO_CYPHER.items():
            suffix = "_" + op_name
            if key.endswith(suffix):
                field = key[: -len(suffix)]
                column = _FIELD_TO_COLUMN[field]
                alternatives = " OR ".join(f"{column} {cypher_op} {_quote(v)}" for v in values)
                clauses.append(f"({alternatives})")
                break
    return " AND ".join(clauses) if clauses else ""


def _build_condition(match: Optional[Dict[str, Any]]) -> str:
    if not match:
        return ""
    if "any" in match:
        groups = [_build_single_group(g) for g in match["any"]]
        groups = [g for g in groups if g]
        return "(" + " OR ".join(groups) + ")" if groups else ""
    return _build_single_group(match)


def _build_where(rule: Dict[str, Any]) -> str:
    parts = []
    match_cond = _build_condition(rule.get("match"))
    if match_cond:
        parts.append(match_cond)
    exclude_cond = _build_condition(rule.get("exclude"))
    if exclude_cond:
        parts.append(f"NOT ({exclude_cond})")
    return " AND ".join(parts) if parts else "true"


def _build_query(rule: Dict[str, Any]) -> str:
    where = _build_where(rule)
    if rule.get("node_type") == "Method":
        query = f"MATCH (m:Method) WHERE {where} RETURN m.className + '.' + m.methodName AS callee, m.sampleCount AS count"
        order = rule.get("order_by")
        if order:
            query += f" ORDER BY m.{order['field']} {order.get('direction', 'DESC')}"
        if rule.get("limit"):
            query += f" LIMIT {rule['limit']}"
        return query

    query = (
        f"MATCH (a:Method)-[r:CALLS]->(b:Method) WHERE {where} "
        f"RETURN a.className + '.' + a.methodName AS caller, "
        f"b.className + '.' + b.methodName AS callee, r.count AS count, r.percent AS pct "
        f"ORDER BY r.count DESC"
    )
    return query


def _threshold_value(rule: Dict[str, Any], count: int, pct: float):
    threshold = rule.get("threshold")
    if not threshold:
        return None
    field = threshold.get("field", "count")
    return pct if field == "percent" else count


def _passes_threshold(rule: Dict[str, Any], count: int, pct: float) -> bool:
    threshold = rule.get("threshold")
    if not threshold:
        return True
    op_fn = _THRESHOLD_OPS[threshold["op"]]
    value = _threshold_value(rule, count, pct)
    return op_fn(value, threshold["value"])


def _severity_for(rule: Dict[str, Any], caller: str, count: int, pct: float) -> str:
    override = rule.get("severity_override")
    if not override:
        return rule["severity"]
    if "low_if_percent_lte" in override and pct <= override["low_if_percent_lte"]:
        return "LOW"
    if "low_if_count_lte" in override and count <= override["low_if_count_lte"]:
        return "LOW"
    if any(s in caller for s in override.get("low_if_caller_contains", [])):
        return "LOW"
    return rule["severity"]


def _total_method_samples(conn) -> int:
    res = conn.execute("MATCH (m:Method) RETURN sum(m.sampleCount)")
    if res.has_next():
        total = res.get_next()[0]
        return int(total) if total else 0
    return 0


def _run_rule(conn, rule: Dict[str, Any], total_method_samples: int) -> List[dict]:
    anomalies = []
    query = _build_query(rule)
    res = conn.execute(query)
    is_single_node = rule.get("node_type") == "Method"

    while res.has_next():
        if is_single_node:
            callee, count = res.get_next()
            caller = rule.get("caller_label", "")
            pct = round((count / total_method_samples) * 100, 4) if total_method_samples else 0.0
        else:
            caller, callee, count, pct = res.get_next()

        if not _passes_threshold(rule, count, pct):
            continue

        anomalies.append({
            "taxonomy_id": rule["primary_taxonomy"],
            "category": rule["category"],
            "type": rule["id"],
            "severity": _severity_for(rule, caller, count, pct),
            "caller": caller,
            "callee": callee,
            "sample_count": count,
            "percentage": pct,
            "description": rule["description_template"].format(caller=caller, callee=callee, count=count, pct=pct),
        })
    return anomalies


def run(conn, taxonomy: str) -> List[dict]:
    anomalies = []
    total_method_samples = None
    for rule in _load_rules():
        if rule["primary_taxonomy"] != taxonomy:
            continue
        if rule.get("node_type") == "Method" and total_method_samples is None:
            total_method_samples = _total_method_samples(conn)
        anomalies.extend(_run_rule(conn, rule, total_method_samples or 0))
    return anomalies
