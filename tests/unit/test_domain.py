"""Pytest unit tests for burn_job.domain models."""

from pathlib import Path
import pytest
from burn_job.domain.finding import Finding, Anomaly, Severity, SourceLocation
from burn_job.domain.endpoint import EndpointInfo, Endpoint
from burn_job.domain.metrics import Metric, MetricSource, LatencyStats, MicrometerMetrics
from burn_job.domain.variant import CodeVariant, ScoringResult, Variant
from burn_job.domain.pipeline_context import PipelineContext, PipelineStatus

def test_finding_domain_model():
    finding = Finding(
        id="f_001",
        taxonomy_id="T1_REDUNDANT_OPS",
        category="Performance",
        type="RedundantOps",
        title="Redundant Loop Operation",
        description="Unnecessary calculation inside loop",
        file="Service.java",
        line=15,
        status="DEFECT",
        evidence={"samples": 120},
    )
    d = finding.to_dict()
    assert d["id"] == "f_001"
    assert d["taxonomy_id"] == "T1_REDUNDANT_OPS"
    assert d["file"] == "Service.java"
    assert d["evidence"]["samples"] == 120

def test_endpoint_domain_model():
    ep = EndpointInfo(
        path="/api/v1/users",
        http_method="GET",
        controller_class="UserController",
        method_name="listUsers",
        file_path="UserController.java",
        line_number=20,
    )
    d = ep.to_dict()
    assert d["path"] == "/api/v1/users"
    assert d["http_method"] == "GET"
    assert ep == Endpoint(path="/api/v1/users", http_method="GET", controller_class="UserController", method_name="listUsers", file_path="UserController.java", line_number=20)

def test_metrics_domain_model():
    m = Metric(name="cpu_usage", value=85.5, unit="pct", source=MetricSource.DYNAMIC_ASYNC_PROFILER)
    assert m.name == "cpu_usage"
    assert m.value == 85.5
    assert m.source == MetricSource.DYNAMIC_ASYNC_PROFILER

    stats = LatencyStats(p50=10.0, p95=45.0, p99=90.0)
    mm = MicrometerMetrics(endpoint="/api/v1/users", rps=150.0, latency=stats)
    d = mm.to_dict()
    assert d["endpoint"] == "/api/v1/users"
    assert d["latency"]["p95"] == 45.0

def test_variant_domain_model():
    v = CodeVariant(
        variant_id="v_001",
        target_file="Service.java",
        code_content="public class Service {}",
        compiles=True,
    )
    assert v.variant_id == "v_001"
    assert v.compiles is True

    sr = ScoringResult(
        variant_id="v_001",
        latency_p95_delta_pct=15.5,
        rps_delta_pct=10.0,
        gc_delta_pct=5.0,
        score=0.85,
        is_winner=True,
    )
    d = sr.to_dict()
    assert d["variant_id"] == "v_001"
    assert d["score"] == 0.85
    assert d["is_winner"] is True

def test_pipeline_context_model():
    target = Path("/tmp/app")
    db = Path("/tmp/db")
    ctx = PipelineContext(target_path=target, db_path=db, status=PipelineStatus.INIT)
    assert ctx.target_path == target
    assert ctx.status == PipelineStatus.INIT
    assert ctx.findings == ()
