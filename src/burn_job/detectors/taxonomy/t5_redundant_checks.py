#!/usr/bin/env python3
"""
T5. Redundant Checks (Dead Code / Duplicate Validation)
"""

import sys
import os

_SCRIPTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)

from burn_job.detectors import rule_engine

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def analyze_t5(conn, reachable_methods=None, declared_methods=None) -> list:
    if not HAS_KUZU:
        return []
    anomalies = []
    cypher_anomalies = rule_engine.run(conn, "T5")
    for a in cypher_anomalies:
        callee = a.get("callee", "")
        if callee and declared_methods is not None and reachable_methods is not None:
            normalized = callee.replace("/", ".")
            if normalized in declared_methods and normalized not in reachable_methods:
                a["type"] = "DEAD_OR_UNREACHABLE_CODE"
                a["severity"] = "HIGH"
                anomalies.append(a)
                continue
        anomalies.append(a)
    return anomalies
