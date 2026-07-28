"""Pytest unit tests for burn_job.detectors module."""

import pytest
from burn_job.detectors.base import BaseDetector
from burn_job.detectors.rule_engine import RuleEngine
from burn_job.detectors.taxonomy.t1_redundant_ops import T1RedundantOpsDetector
from burn_job.core.protocols import DetectorProtocol

class CustomTestDetector(BaseDetector):
    def __init__(self):
        super().__init__(rule_id="T10_CUSTOM", name="Custom Test Detector")

def test_base_detector_properties():
    detector = CustomTestDetector()
    assert detector.rule_id == "T10_CUSTOM"
    assert detector.name == "Custom Test Detector"
    assert isinstance(detector, DetectorProtocol)

def test_t1_redundant_ops_detector():
    detector = T1RedundantOpsDetector()
    assert detector.rule_id == "T1_REDUNDANT_OPS"
    assert isinstance(detector, DetectorProtocol)

def test_rule_engine_register_and_run():
    engine = RuleEngine()
    detector = T1RedundantOpsDetector()
    engine.register(detector)
    
    registered = engine.get_registered_detectors()
    assert len(registered) == 1
    assert registered[0] == detector

    findings = engine.run_all(context=None)
    assert isinstance(findings, tuple)
