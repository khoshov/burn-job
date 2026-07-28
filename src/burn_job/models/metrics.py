"""
Metrics Domain Models.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class LatencyStats:
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


@dataclass
class MicrometerMetrics:
    """Represents captured Spring Actuator / Micrometer metrics."""
    endpoint: str
    rps: float = 0.0
    latency: LatencyStats = field(default_factory=LatencyStats)
    gc_allocations_mb: float = 0.0
    error_count: int = 0
    total_requests: int = 0

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "rps": self.rps,
            "latency": {
                "p50": self.latency.p50,
                "p95": self.latency.p95,
                "p99": self.latency.p99,
            },
            "gc_allocations_mb": self.gc_allocations_mb,
            "error_count": self.error_count,
            "total_requests": self.total_requests,
        }
