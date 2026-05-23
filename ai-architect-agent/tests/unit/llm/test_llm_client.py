"""Unit tests for the provider-abstracted LLM client."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.client import FAST_MODEL_STAGES, LLMClient, LLMProvider

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}


def test_initialises_with_ollama_provider_when_env_var_set() -> None:
    """LLMClient uses Ollama when LLM_PROVIDER=ollama."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    assert client._provider == LLMProvider.OLLAMA


def test_initialises_with_openai_provider_when_env_var_set() -> None:
    """LLMClient uses OpenAI when LLM_PROVIDER=openai."""
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"},
        clear=False,
    ):
        client = LLMClient()

    assert client._provider == LLMProvider.OPENAI


def test_select_model_returns_fast_model_for_fast_stages() -> None:
    """Fast-model stages use the configured fast model."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    for stage_name in FAST_MODEL_STAGES:
        model, _ = client._select_model(stage_name)
        assert model == client._fast_model


def test_select_model_returns_primary_model_for_reasoning_stage() -> None:
    """Reasoning stages use the configured primary model."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    model, _ = client._select_model("architecture_generation")

    assert model == client._primary_model


def test_select_model_returns_openai_model_for_openai_provider() -> None:
    """OpenAI provider always returns the OpenAI model."""
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"},
        clear=False,
    ):
        client = LLMClient()

    model, context_window = client._select_model("requirement_parsing")

    assert model == client._openai_model
    assert context_window == 128000


@pytest.mark.asyncio
async def test_complete_ollama_passes_schema_as_format() -> None:
    """Ollama receives the schema dict as native format."""
    client, captured_payload = _ollama_client_with_transport()

    await client._complete_ollama(
        "prompt", "json", SAMPLE_SCHEMA, "requirement_parsing"
    )
    client._test_patcher.stop()

    assert captured_payload["format"] == SAMPLE_SCHEMA


@pytest.mark.asyncio
async def test_complete_ollama_passes_json_format_without_schema() -> None:
    """Ollama receives format=json when no schema is provided."""
    client, captured_payload = _ollama_client_with_transport()

    await client._complete_ollama("prompt", "json", None, "requirement_parsing")
    client._test_patcher.stop()

    assert captured_payload["format"] == "json"


@pytest.mark.asyncio
async def test_complete_ollama_passes_num_ctx_in_options() -> None:
    """Ollama options include the selected context window."""
    client, captured_payload = _ollama_client_with_transport()

    await client._complete_ollama("prompt", "json", None, "requirement_parsing")
    client._test_patcher.stop()

    assert captured_payload["options"]["num_ctx"] == client._num_ctx_fast


@pytest.mark.asyncio
async def test_complete_ollama_passes_temperature_in_options() -> None:
    """Ollama options include the configured temperature."""
    client, captured_payload = _ollama_client_with_transport()

    await client._complete_ollama("prompt", "json", None, "requirement_parsing")
    client._test_patcher.stop()

    assert captured_payload["options"]["temperature"] == client._temperature


def test_timeout_for_stage_returns_300_for_ollama_reasoning_stage() -> None:
    """Ollama reasoning stages receive the long timeout."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    assert client._timeout_for_stage("architecture_generation") == 300


def test_timeout_for_stage_returns_120_for_openai() -> None:
    """OpenAI provider keeps the shorter API timeout."""
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"},
        clear=False,
    ):
        client = LLMClient()

    assert client._timeout_for_stage("architecture_generation") == 120


def test_max_tokens_for_stage_returns_reasonable_fraction_of_context() -> None:
    """Output token budget remains bounded by context and absolute cap."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    assert client._max_tokens_for_stage("architecture_generation", 8192) == 3276
    assert client._max_tokens_for_stage("requirement_parsing", 8192) == 2048


@pytest.mark.asyncio
async def test_openai_structured_output_uses_json_schema() -> None:
    """OpenAI receives strict json_schema response_format."""
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"},
        clear=False,
    ):
        client = LLMClient()
    client._openai_client = MagicMock()
    client._openai_client.chat.completions.create = AsyncMock(
        return_value=_openai_response()
    )

    response_format = None

    async def capture_create(**kwargs):
        nonlocal response_format
        response_format = kwargs["response_format"]
        return _openai_response()

    client._openai_client.chat.completions.create.side_effect = capture_create

    await client._complete_openai("prompt", "json", SAMPLE_SCHEMA, "sample")

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True


def _ollama_client_with_transport() -> tuple[LLMClient, dict]:
    """Create an Ollama client with a capturing httpx transport."""
    captured_payload: dict = {}

    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
        client = LLMClient()

    class CapturingAsyncClient:
        """Minimal async context manager that captures request JSON."""

        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self) -> "CapturingAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, json: dict) -> MagicMock:
            captured_payload.update(json)
            response = MagicMock()
            response.json.return_value = {"response": '{"name":"ok"}'}
            response.raise_for_status.return_value = None
            return response

    patcher = patch("app.llm.client.httpx.AsyncClient", CapturingAsyncClient)
    client._test_patcher = patcher
    patcher.start()
    return client, captured_payload


def _openai_response() -> MagicMock:
    """Return a minimal OpenAI chat completion response."""
    message = MagicMock()
    message.content = '{"name":"ok"}'
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response
