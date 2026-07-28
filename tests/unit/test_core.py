"""Pytest unit tests for burn_job.core package."""

import os
import pytest
import logging
from burn_job.core.config import Config, DEFAULT_DB_PATH, DEFAULT_HOST
from burn_job.core.exceptions import (
    BurnJobError,
    ConfigurationError,
    DetectorError,
    DetectorExecutionError,
    GraphStoreError,
    PipelineExecutionError,
)
from burn_job.core.logging import setup_logger
from burn_job.core.protocols import DetectorProtocol, StoreProtocol

def test_config_defaults():
    cfg = Config()
    assert cfg.host == DEFAULT_HOST
    assert cfg.db_path == DEFAULT_DB_PATH
    assert cfg.concurrency == 50

def test_exceptions_hierarchy():
    with pytest.raises(BurnJobError):
        raise ConfigurationError("Invalid config")

    with pytest.raises(DetectorError):
        raise DetectorExecutionError("Detector failed")

    with pytest.raises(BurnJobError):
        raise GraphStoreError("Store failed")

    with pytest.raises(BurnJobError):
        raise PipelineExecutionError("Pipeline failed")

def test_setup_logger():
    logger = setup_logger("test_core_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_core_logger"

class DummyDetector:
    @property
    def rule_id(self) -> str:
        return "T0_DUMMY"

    @property
    def name(self) -> str:
        return "Dummy"

    def analyze(self, context):
        return ()

def test_detector_protocol():
    detector = DummyDetector()
    assert isinstance(detector, DetectorProtocol)
