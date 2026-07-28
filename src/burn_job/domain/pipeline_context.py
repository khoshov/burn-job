"""PipelineContext state container model."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from burn_job.domain.finding import Finding
from burn_job.domain.endpoint import EndpointInfo
from burn_job.domain.metrics import Metric, MicrometerMetrics
from burn_job.domain.variant import CodeVariant, ScoringResult

class PipelineStatus(str, Enum):
    INIT = "INIT"
    SCANNED = "SCANNED"
    INGESTED = "INGESTED"
    ANALYZED = "ANALYZED"
    REFINED = "REFINED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class PipelineContext:
    """Immutable state container passed sequentially across pipeline stages."""
    target_path: Path
    db_path: Path
    endpoints: Tuple[EndpointInfo, ...] = field(default_factory=tuple)
    findings: Tuple[Finding, ...] = field(default_factory=tuple)
    metrics: Tuple[Metric, ...] = field(default_factory=tuple)
    variants: Tuple[CodeVariant, ...] = field(default_factory=tuple)
    status: PipelineStatus = PipelineStatus.INIT
    metadata: Dict[str, Any] = field(default_factory=dict)
