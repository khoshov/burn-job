"""Unit tests for LLMAgent local llama.cpp integration."""

import os
from unittest.mock import MagicMock, patch
import pytest

from burn_job.refinement.agent import LLMAgent, find_default_model_path


def test_find_default_model_path(tmp_path):
    with patch("burn_job.refinement.agent.REPO_ROOT", str(tmp_path)):
        # When no GGUF file exists
        assert find_default_model_path() is None

        # Create mock GGUF file
        model_dir = tmp_path / "Qwen3-4B"
        model_dir.mkdir()
        gguf_file = model_dir / "qwen3-4b-instruct.gguf"
        gguf_file.write_text("fake_gguf")

        found = find_default_model_path()
        assert found is not None
        assert found.endswith(".gguf")


def test_llm_agent_local_mock_inference():
    mock_llama = MagicMock()
    mock_llama.create_chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```java\npublic class OptimizedService {}\n```"
                }
            }
        ]
    }

    agent = LLMAgent(model="qwen3")
    agent.llama_model = mock_llama

    assert agent.is_api_configured() is True
    res = agent.call_llm("Refactor this code")
    assert "OptimizedService" in res

    mock_llama.create_chat_completion.assert_called_once()
    args, kwargs = mock_llama.create_chat_completion.call_args
    assert kwargs["messages"][1]["content"] == "Refactor this code"


def test_llm_agent_unconfigured_error():
    agent = LLMAgent(model="qwen3")
    agent.llama_model = None
    agent.api_key = None

    assert agent.is_api_configured() is False
    with pytest.raises(ValueError, match="LLM API Key or local llama.cpp model path not provided"):
        agent.call_llm("Test prompt")
