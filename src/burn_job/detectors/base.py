"""BaseDetector abstract class and shared source-scanning utilities."""

import os
from abc import ABC, abstractmethod
from typing import List, Tuple, Any

from burn_job.core.protocols import DetectorProtocol
from burn_job.domain.finding import Finding
from burn_job.domain.pipeline_context import PipelineContext
from burn_job.detectors._shared import SRC_ROOT, iter_java_files


class BaseDetector(ABC):
    """Abstract base class for all defect detectors."""

    def __init__(self, rule_id: str = "T0_BASE", name: str = "Base Detector") -> None:
        self._rule_id = rule_id
        self._name = name

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    def detect(self, file_path: str) -> list:
        """Legacy scan method for individual files."""
        return []

    def analyze(self, context: Any) -> Tuple[Finding, ...]:
        """Core protocol analysis entrypoint."""
        findings = []
        if hasattr(context, "target_path") and os.path.exists(str(context.target_path)):
            java_files = iter_java_files(str(context.target_path))
            for fpath in java_files:
                findings.extend(self.detect(fpath))
        return tuple(findings)
