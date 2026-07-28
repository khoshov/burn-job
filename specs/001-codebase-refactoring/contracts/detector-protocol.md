# Detector Interface Protocol & Contract

**Feature**: Codebase Architecture & Structure Refactoring
**Spec**: [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md)

---

## Python Interface Protocol (`burn_job.core.protocols`)

All defect detectors (static AST, byte-code `javap`, dynamic profile analyzers) MUST implement the `DetectorProtocol` typing protocol.

```python
from typing import Protocol, Tuple, runtime_checkable
from burn_job.domain.finding import Finding
from burn_job.domain.pipeline_context import PipelineContext

@runtime_checkable
class DetectorProtocol(Protocol):
    """Protocol defining mandatory capabilities for all performance defect detectors."""
    
    @property
    def rule_id(self) -> str:
        """Return the taxonomy rule identifier (e.g. 'T1_REDUNDANT_OPS')."""
        ...
        
    @property
    def name(self) -> str:
        """Return human-readable detector name."""
        ...

    def analyze(self, context: PipelineContext) -> Tuple[Finding, ...]:
        """Analyze the target application context and return identified findings.
        
        Args:
            context: Immutable pipeline context with target path, graph DB handle, and metrics.
            
        Returns:
            Tuple of Finding domain objects discovered by this detector.
            
        Raises:
            DetectorExecutionError: If analysis fails non-recoverably.
        """
        ...
```

---

## Base Implementation (`burn_job.detectors.base`)

Abstract base class `BaseDetector` provides optional helper utilities for taxonomy rules:

```python
from abc import ABC, abstractmethod
from typing import Tuple
from burn_job.domain.finding import Finding
from burn_job.domain.pipeline_context import PipelineContext

class BaseDetector(ABC):
    """Abstract base class providing shared logging and metric extraction helpers."""
    
    def __init__(self, rule_id: str, name: str) -> None:
        self._rule_id = rule_id
        self._name = name
        
    @property
    def rule_id(self) -> str:
        return self._rule_id
        
    @property
    def name(self) -> str:
        return self._name
        
    @abstractmethod
    def analyze(self, context: PipelineContext) -> Tuple[Finding, ...]:
        """Core analysis method to be overridden by subclasses."""
        pass
```
