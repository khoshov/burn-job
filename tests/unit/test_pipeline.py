"""Pytest unit tests for burn_job.pipeline module."""

import tempfile
import os
import pytest
from burn_job.domain.endpoint import EndpointInfo
from burn_job.pipeline.scanner import ControllerScanner
from burn_job.pipeline.loadtest import LoadtestGenerator
from burn_job.pipeline.scorer import ScoringEvaluator
from burn_job.domain.variant import ScoringResult

def test_controller_scanner_empty_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        endpoints = ControllerScanner.scan_directory(tmp_dir)
        assert endpoints == []

def test_controller_scanner_mock_controller():
    with tempfile.TemporaryDirectory() as tmp_dir:
        controller_file = os.path.join(tmp_dir, "TestController.java")
        with open(controller_file, "w", encoding="utf-8") as f:
            f.write("""
package com.example;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class TestController {
    @GetMapping("/api/test")
    public String getTest() {
        return "ok";
    }
}
""")
        endpoints = ControllerScanner.scan_directory(tmp_dir)
        assert len(endpoints) == 1
        assert endpoints[0].path == "/api/test"
        assert endpoints[0].http_method == "GET"
        assert endpoints[0].controller_class == "TestController"

def test_loadtest_generator():
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_script = os.path.join(tmp_dir, "loadtest_suite.py")
        endpoints = [EndpointInfo(path="/api/test", http_method="GET")]
        LoadtestGenerator.generate_script(endpoints, output_script)
        assert os.path.exists(output_script)
        with open(output_script, "r", encoding="utf-8") as f:
            content = f.read()
        assert "/api/test" in content

def test_scoring_evaluator():
    res = ScoringEvaluator.calculate_score(
        variant_id="v1",
        base_p95=100.0,
        var_p95=50.0,
        base_rps=1000.0,
        var_rps=1500.0,
        base_gc=100.0,
        var_gc=80.0,
    )
    assert isinstance(res, ScoringResult)
    assert res.variant_id == "v1"
    assert res.latency_p95_delta_pct == 50.0
    assert res.rps_delta_pct == 50.0
    assert res.gc_delta_pct == 20.0
    assert res.score > 0

def test_scoring_evaluator_select_winner():
    r1 = ScoringResult(variant_id="v1", score=10.5)
    r2 = ScoringResult(variant_id="v2", score=25.0)
    winner = ScoringEvaluator.select_winner([r1, r2])
    assert winner.variant_id == "v2"
    assert winner.is_winner is True
