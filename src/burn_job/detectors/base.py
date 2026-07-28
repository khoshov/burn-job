"""BaseDetector abstract class and shared source-scanning utilities."""

import os
from abc import ABC, abstractmethod
from typing import List, Tuple, Any

from burn_job.core.protocols import DetectorProtocol
from burn_job.domain.finding import Finding
from burn_job.domain.pipeline_context import PipelineContext

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "java", "src", "main", "java")

def _iter_java_files(src_root: str = SRC_ROOT) -> List[str]:
    if not os.path.isdir(src_root):
        return []
    files = []
    for dirpath, _dirs, filenames in os.walk(src_root):
        for fname in filenames:
            if fname.endswith(".java"):
                files.append(os.path.join(dirpath, fname))
    return files

def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1

def _scan_braces(text: str, open_index: int) -> int:
    depth = 0
    i = open_index
    n = len(text)
    in_line_comment = in_block_comment = in_string = in_char = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
        elif in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if c == "\\":
                i += 1
            elif c == '"':
                in_string = False
        elif in_char:
            if c == "\\":
                i += 1
            elif c == "'":
                in_char = False
        else:
            if c == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif c == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return n - 1

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
        if hasattr(context, "target_path") and os.path.exists(context.target_path):
            java_files = _iter_java_files(str(context.target_path))
            for fpath in java_files:
                findings.extend(self.detect(fpath))
        return tuple(findings)
