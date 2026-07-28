"""Pytest integration test for domain entities and PipelineContext initialization."""

import os
import tempfile
from pathlib import Path
from burn_job.domain import (
    Finding,
    EndpointInfo,
    Metric,
    MetricSource,
    CodeVariant,
    PipelineContext,
    PipelineStatus,
)
from burn_job.graph import KuzuGraphStore

def test_pipeline_context_initialization():
    target = Path("/tmp/target_repo")
    db = Path("/tmp/test_db")

    finding = Finding(
        id="f1",
        taxonomy_id="T1_REDUNDANT_OPS",
        category="Algorithmic",
        type="RedundantOps",
        title="Redundant Operations",
        description="Found unnecessary loop calculations",
        file="Controller.java",
        line=42,
    )

    endpoint = EndpointInfo(
        path="/api/test",
        http_method="GET",
        controller_class="TestController",
        method_name="getTest",
    )

    metric = Metric(
        name="nesting_depth",
        value=4.0,
        unit="depth",
        source=MetricSource.STATIC_AST,
    )

    variant = CodeVariant(
        variant_id="v1",
        target_file="Controller.java",
        code_content="class Controller {}",
        compiles=True,
    )

    context = PipelineContext(
        target_path=target,
        db_path=db,
        endpoints=(endpoint,),
        findings=(finding,),
        metrics=(metric,),
        variants=(variant,),
        status=PipelineStatus.INIT,
    )

    assert context.target_path == target
    assert len(context.findings) == 1
    assert context.findings[0].id == "f1"
    assert context.status == PipelineStatus.INIT

def test_graph_store_instantiation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_kuzu_db_file")
        store = KuzuGraphStore(db_path=db_path)
        assert store is not None
