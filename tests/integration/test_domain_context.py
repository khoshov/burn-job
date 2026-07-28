"""Integration test for domain entities and PipelineContext initialization."""

import unittest
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

class TestDomainContext(unittest.TestCase):

    def test_pipeline_context_initialization(self):
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

        self.assertEqual(context.target_path, target)
        self.assertEqual(len(context.findings), 1)
        self.assertEqual(context.findings[0].id, "f1")
        self.assertEqual(context.status, PipelineStatus.INIT)

    def test_graph_store_instantiation(self):
        store = KuzuGraphStore(db_path="/tmp/test_kuzu_store")
        self.assertIsNotNone(store)

if __name__ == "__main__":
    unittest.main()
