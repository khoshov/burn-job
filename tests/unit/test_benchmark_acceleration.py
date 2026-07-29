"""Unit tests for benchmarking acceleration and pre-filtering."""

import pytest
from unittest.mock import MagicMock, patch, mock_open

from burn_job.pipeline.orchestrator import AutonomousOrchestrator


def test_skip_benchmark_active_skips_live_benchmarking():
    """Verify that skip_benchmark=True returns findings immediately without benchmarking."""
    orchestrator = AutonomousOrchestrator(skip_benchmark=True)
    findings = [
        {"file": "src/Controller.java", "variants": [{"strategy": "T1", "score": 90.0}], "winner": {"strategy": "T1"}}
    ]

    res = orchestrator._benchmark_variants(findings)
    assert res == findings


def test_benchmark_variants_skips_failed_compilation_precheck():
    """Verify variants with compiles=False are skipped before starting Spring Boot / Maven."""
    orchestrator = AutonomousOrchestrator(skip_benchmark=False)

    findings = [
        {
            "file": "test_project/src/main/java/com/example/Controller.java",
            "variants": [
                {
                    "strategy": "Invalid Strategy",
                    "generated_code": "class Invalid {",
                    "compiles": False,  # Precheck failed
                }
            ],
        }
    ]

    with patch("burn_job.pipeline.orchestrator.AutonomousOrchestrator._find_project_dir", return_value="/tmp"):
        with patch("burn_job.pipeline.orchestrator.AutonomousOrchestrator._resolve_finding_file", return_value="/tmp/Controller.java"):
            with patch("builtins.open", mock_open(read_data="public class Controller {}")):
                res = orchestrator._benchmark_variants(findings)
                var = res[0]["variants"][0]
                assert var["benchmark"]["error"] == "compilation_failed_precheck"


def test_benchmark_with_micrometer_parallel_execution():
    """Verify _benchmark_with_micrometer handles load requests in parallel without errors."""
    orchestrator = AutonomousOrchestrator()

    mock_metrics_before = {"COUNT": 100, "TOTAL_TIME": 10.0, "MAX": 0.5}
    mock_metrics_after = {"COUNT": 650, "TOTAL_TIME": 35.0, "MAX": 0.5}

    with patch.object(orchestrator, "_read_micrometer_metric", side_effect=[mock_metrics_before, mock_metrics_after]):
        with patch("urllib.request.urlopen", return_value=MagicMock()):
            res = orchestrator._benchmark_with_micrometer("/api/test", warmup=10, measure=50)
            assert res["count"] == 550
            assert res["total_time_s"] == 25.0
            assert "avg_s" in res
