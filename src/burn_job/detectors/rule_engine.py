"""Generic engine and registry for defect detectors and graph_rules.yaml."""

import os
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

def _load_rules() -> List[Dict[str, Any]]:
    if not HAS_YAML or not os.path.exists(RULES_PATH):
        return []
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])

def run(conn, taxonomy: str) -> List[dict]:
    anomalies = []
    # Placeholder for graph_rules execution
    return anomalies
