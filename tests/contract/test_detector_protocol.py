"""Contract test verifying all taxonomy detectors implement DetectorProtocol."""

import unittest
from burn_job.core.protocols import DetectorProtocol
from burn_job.detectors import BaseDetector, RuleEngine, T1RedundantOpsDetector

class TestDetectorProtocolContract(unittest.TestCase):

    def test_t1_detector_implements_protocol(self):
        detector = T1RedundantOpsDetector()
        self.assertTrue(isinstance(detector, DetectorProtocol))
        self.assertEqual(detector.rule_id, "T1_REDUNDANT_OPS")
        self.assertEqual(detector.name, "Redundant Operations Detector")

    def test_rule_engine_registration(self):
        engine = RuleEngine()
        detector = T1RedundantOpsDetector()
        engine.register(detector)
        registered = engine.get_registered_detectors()
        self.assertEqual(len(registered), 1)
        self.assertIn(detector, registered)

if __name__ == "__main__":
    unittest.main()
