"""Core Protocol definitions for structural subtyping."""

from typing import Any, Dict, Protocol, Tuple, runtime_checkable

@runtime_checkable
class DetectorProtocol(Protocol):
    """Protocol defining mandatory capabilities for all performance defect detectors."""
    
    @property
    def rule_id(self) -> str:
        """Taxonomy rule identifier (e.g. 'T1_REDUNDANT_OPS')."""
        ...
        
    @property
    def name(self) -> str:
        """Human-readable detector name."""
        ...

    def analyze(self, context: Any) -> Tuple[Any, ...]:
        """Analyze pipeline context and return findings."""
        ...

@runtime_checkable
class StoreProtocol(Protocol):
    """Protocol for graph database storage adapters."""
    
    def connect(self) -> None:
        ...
        
    def close(self) -> None:
        ...
        
    def execute_query(self, cypher_query: str, params: Dict[str, Any] = ...) -> Any:
        ...

@runtime_checkable
class ReportBuilderProtocol(Protocol):
    """Protocol for performance report builders."""
    
    def build(self, context: Any) -> str:
        ...
