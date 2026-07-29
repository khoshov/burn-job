"""Unit tests for Phase 2 DeepSeek acceleration optimizations (caching & fast syntax pre-validation)."""

import pytest
from unittest.mock import MagicMock

from burn_job.detectors.variant_comparison import (
    _quick_syntax_check,
    fetch_candidate_codes_from_llm,
    generate_and_evaluate_variants,
    _CANDIDATE_CACHE,
)


def test_quick_syntax_check_valid_and_invalid():
    """Verify fast in-memory Java syntax pre-validation."""
    valid_code = "public class Foo { public void test() { return; } }"
    invalid_unbalanced = "public class Foo { public void test() { return; "
    invalid_no_keywords = "hello world text with no java keywords"

    assert _quick_syntax_check(valid_code) is True
    assert _quick_syntax_check(invalid_unbalanced) is False
    assert _quick_syntax_check(invalid_no_keywords) is False
    assert _quick_syntax_check("") is False


def test_candidate_cache_hit():
    """Verify duplicate finding calls hit the candidate cache instantly."""
    _CANDIDATE_CACHE.clear()

    mock_agent = MagicMock()
    mock_agent.is_api_configured.return_value = True
    mock_agent.api_key = "sk-key"
    mock_agent.call_llm_api.return_value = "API response"
    mock_agent.extract_multi_code_blocks.return_value = {"v1": "class Cached {}"}

    finding = {"pdf_taxonomy": ["T1"], "mechanism": "N+1 loop"}
    orig_code = "public class Original {}"
    target_file = "/tmp/Original.java"

    # First call: hits agent API
    res1 = fetch_candidate_codes_from_llm(finding, orig_code, target_file, agent=mock_agent, variant_llm="deepseek")
    assert res1 == {"v1": "class Cached {}"}
    assert mock_agent.call_llm_api.call_count == 1

    # Second call: hits cache, API call count stays 1
    res2 = fetch_candidate_codes_from_llm(finding, orig_code, target_file, agent=mock_agent, variant_llm="deepseek")
    assert res2 == {"v1": "class Cached {}"}
    assert mock_agent.call_llm_api.call_count == 1


def test_fast_syntax_precheck_bypasses_maven():
    """Verify syntactically invalid candidates are flagged without disk/mvn execution."""
    mock_verify = MagicMock()

    finding = {"pdf_taxonomy": ["T1"], "mechanism": "N+1"}
    orig_code = "public class Foo {}"
    target_file = "/tmp/Foo.java"

    invalid_candidates = {"v1": "invalid java syntax {"}

    variants = generate_and_evaluate_variants(
        finding=finding,
        original_code=orig_code,
        target_file=target_file,
        verify_compile=True,
        prefetched_candidates=invalid_candidates,
    )

    v1 = next(v for v in variants if v["strategy"] == "Batch Lookup & Map Indexing")
    assert v1["compiles"] is False
    assert "fast_syntax_precheck_failed" in v1["errors"]
