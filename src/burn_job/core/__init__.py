"""Burn-Job Core Package."""

from burn_job.core.config import Config, DEFAULT_DB_PATH, DEFAULT_PROFILE_PATH, RUN_LOG_PATH
from burn_job.core.exceptions import (
    BurnJobError,
    ConfigurationError,
    DetectorError,
    DetectorExecutionError,
    GraphStoreError,
    PipelineExecutionError,
)
from burn_job.core.logging import setup_logger
from burn_job.core.protocols import DetectorProtocol, StoreProtocol, ReportBuilderProtocol

__all__ = [
    "Config",
    "DEFAULT_DB_PATH",
    "DEFAULT_PROFILE_PATH",
    "RUN_LOG_PATH",
    "BurnJobError",
    "ConfigurationError",
    "DetectorError",
    "DetectorExecutionError",
    "GraphStoreError",
    "PipelineExecutionError",
    "setup_logger",
    "DetectorProtocol",
    "StoreProtocol",
    "ReportBuilderProtocol",
]
