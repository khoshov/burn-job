"""Finding and Anomaly Domain Models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass(frozen=True)
class SourceLocation:
    """Represents a location in source code."""
    file_path: str
    line_number: int = 0
    end_line_number: int = 0
    method_name: str = ""

@dataclass
class Anomaly:
    """Represents a performance anomaly extracted from graph/profiler data."""
    taxonomy_id: str
    category: str
    type: str
    caller: str
    callee: str
    sample_count: int
    status: str = "DEFECT"
    non_defect_rule: Optional[str] = None
    non_defect_title: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Finding:
    """Represents a schema-compliant issue finding for LLM Agent refactoring."""
    id: str
    taxonomy_id: str
    category: str
    type: str
    title: str
    description: str
    file: str
    line: int
    status: str = "DEFECT"
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxonomy_id": self.taxonomy_id,
            "category": self.category,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "status": self.status,
            "evidence": self.evidence,
        }
