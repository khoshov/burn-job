"""Code Variant & Scoring Result Domain Models."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class CodeVariant:
    """Represents a code optimization candidate variant (v1, v2, etc.)."""
    variant_id: str
    target_file: str
    code_content: str
    compiles: bool = False
    compile_error: Optional[str] = None

@dataclass
class ScoringResult:
    """Represents the benchmark scoring result of a variant relative to baseline."""
    variant_id: str
    latency_p95_delta_pct: float = 0.0
    rps_delta_pct: float = 0.0
    gc_delta_pct: float = 0.0
    score: float = 0.0
    is_winner: bool = False

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "latency_p95_delta_pct": self.latency_p95_delta_pct,
            "rps_delta_pct": self.rps_delta_pct,
            "gc_delta_pct": self.gc_delta_pct,
            "score": round(self.score, 4),
            "is_winner": self.is_winner,
        }

# Alias Variant to CodeVariant for contract consistency
Variant = CodeVariant
