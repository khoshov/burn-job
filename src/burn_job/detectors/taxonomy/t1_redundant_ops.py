"""T1. Redundant Computations & Operations Detector."""

from burn_job.detectors.base import BaseDetector
from burn_job.detectors import rule_engine

class T1RedundantOpsDetector(BaseDetector):
    def __init__(self) -> None:
        super().__init__(rule_id="T1_REDUNDANT_OPS", name="Redundant Operations Detector")

def analyze_t1(conn) -> list:
    return rule_engine.run(conn, "T1")
