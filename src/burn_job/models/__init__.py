"""
Dataclasses and Domain Models for Performance Optimization Pipeline.
"""

from burn_job.models.endpoint import EndpointInfo
from burn_job.models.finding import Finding, Anomaly
from burn_job.models.metrics import MicrometerMetrics, LatencyStats
from burn_job.models.variant import CodeVariant, ScoringResult

__all__ = [
    "EndpointInfo",
    "Finding",
    "Anomaly",
    "MicrometerMetrics",
    "LatencyStats",
    "CodeVariant",
    "ScoringResult",
]
