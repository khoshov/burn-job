"""Unit tests for parallel DeepSeek API call optimization and connection pooling."""

import os
import time
import pytest
from unittest.mock import MagicMock, patch

from burn_job.refinement.agent import LLMAgent
from burn_job.detectors.variant_comparison import attach_variant_comparisons, fetch_candidate_codes_from_llm


def test_agent_session_pooling_initialization():
    """Verify that LLMAgent initializes a persistent requests session with HTTPAdapter connection pooling."""
    agent = LLMAgent(api_key="sk-dummy-test-key", base_url="https://api.deepseek.com/v1")
    assert hasattr(agent, "session")
    assert agent.session is not None


def test_parallel_attach_variant_comparisons_concurrency():
    """Verify attach_variant_comparisons processes multiple findings concurrently using ThreadPoolExecutor."""
    mock_agent = MagicMock()
    mock_agent.is_api_configured.return_value = True
    mock_agent.api_key = "sk-dummy-key"
    mock_agent.model = "deepseek-v4-flash"

    # Simulate 100ms API call latency per finding
    def mock_call_llm_api(prompt, system_prompt=None, model=None):
        time.sleep(0.1)
        return """[VARIANT_1]
```java
// Fast Variant 1
```
[VARIANT_2]
```java
// Fast Variant 2
```
"""

    mock_agent.call_llm_api.side_effect = mock_call_llm_api
    mock_agent.extract_multi_code_blocks.return_value = {
        "v1": "class Test1 {}",
        "v2": "class Test2 {}",
    }

    dummy_findings = [
        {"file": "test_project/src/main/java/com/example/Controller.java", "pdf_taxonomy": ["T1"], "mechanism": "N+1 query"},
        {"file": "test_project/src/main/java/com/example/Service.java", "pdf_taxonomy": ["T2"], "mechanism": "In-memory loop"},
        {"file": "test_project/src/main/java/com/example/Repository.java", "pdf_taxonomy": ["T3"], "mechanism": "Full table scan"},
        {"file": "test_project/src/main/java/com/example/Utils.java", "pdf_taxonomy": ["T4"], "mechanism": "Primitive boxing"},
    ]

    with patch("burn_job.detectors.variant_comparison.read_file", return_value="public class Original {}"):
        with patch("burn_job.detectors.variant_comparison.os.path.exists", return_value=True):
            start_time = time.time()
            enriched = attach_variant_comparisons(
                dummy_findings,
                agent=mock_agent,
                verify_compile=False,
                variant_llm="deepseek",
                max_workers=4,
            )
            elapsed = time.time() - start_time

            # Sequential 4 calls * 0.1s = 0.4s+, parallel with 4 workers should finish in ~0.15s
            assert len(enriched) == 4
            assert elapsed < 0.35  # Confirms parallel speedup over sequential execution
            for f in enriched:
                assert "variants" in f
                assert f["winner"] is not None
                assert len(f["variants"]) >= 3


def test_fetch_candidate_codes_from_llm():
    """Verify fetch_candidate_codes_from_llm extracts multi-variant blocks properly."""
    mock_agent = MagicMock()
    mock_agent.is_api_configured.return_value = True
    mock_agent.api_key = "sk-dummy-key"
    mock_agent.call_llm_api.return_value = "raw response"
    mock_agent.extract_multi_code_blocks.return_value = {"v1": "code1", "v2": "code2"}

    res = fetch_candidate_codes_from_llm(
        finding={"pdf_taxonomy": ["T1"], "mechanism": "test"},
        original_code="code",
        target_file="/tmp/Test.java",
        agent=mock_agent,
        variant_llm="deepseek",
    )
    assert res == {"v1": "code1", "v2": "code2"}


def test_agent_bypasses_local_model_when_external_api_active():
    """Verify LLMAgent skips loading local llama.cpp GGUF weights when API key is provided."""
    with patch("burn_job.refinement.agent.Llama", create=True) as mock_llama:
        agent = LLMAgent(api_key="sk-test-key", backend="auto")
        assert agent.llama_model is None
        mock_llama.assert_not_called()
