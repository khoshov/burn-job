"""Pytest contract test verifying all taxonomy detectors implement DetectorProtocol."""

from burn_job.core.protocols import DetectorProtocol
from burn_job.detectors import BaseDetector, RuleEngine, T1RedundantOpsDetector

def test_t1_detector_implements_protocol():
    detector = T1RedundantOpsDetector()
    assert isinstance(detector, DetectorProtocol)
    assert detector.rule_id == "T1_REDUNDANT_OPS"
    assert detector.name == "Redundant Operations Detector"

def test_rule_engine_registration():
    engine = RuleEngine()
    detector = T1RedundantOpsDetector()
    engine.register(detector)
    registered = engine.get_registered_detectors()
    assert len(registered) == 1
    assert detector in registered
