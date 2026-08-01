"""Tests for SpecWeaver LLM client helpers."""

from __future__ import annotations

import openai
import pytest

from app.llm.budget import STAGE_OUTPUT_BUDGET, output_budget_for_stage
from app.llm.client import DEFAULT_OPENAI_CONTEXT_WINDOW, LLMClient, LLMProvider


def test_stage_output_budget_contains_specweaver_stages():
    assert STAGE_OUTPUT_BUDGET["extraction"] == 3000
    assert STAGE_OUTPUT_BUDGET["classification"] == 4000
    assert STAGE_OUTPUT_BUDGET["output_formatting"] == 2000


def test_output_budget_for_stage_uses_fallback_for_unknown_stage():
    assert output_budget_for_stage("unknown", 1234) == 1234


def test_strip_markdown_fences_removes_json_fence():
    assert LLMClient._strip_markdown_fences("```json\n{\"ok\": true}\n```") == (
        '{"ok": true}'
    )


def test_select_model_uses_fast_model_for_output_formatting(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", LLMProvider.OLLAMA.value)
    client = LLMClient()
    model, _ = client._select_model("output_formatting")
    assert model == client._fast_model


def test_select_model_uses_openai_model_when_provider_is_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", LLMProvider.OPENAI.value)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeOpenAIClient:
        def __init__(self, api_key: str | None) -> None:
            self.api_key = api_key

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeOpenAIClient)

    client = LLMClient()
    model, context_window = client._select_model("output_formatting")

    assert model == "gpt-4o"
    assert context_window == DEFAULT_OPENAI_CONTEXT_WINDOW


@pytest.mark.asyncio
async def test_openai_falls_back_to_json_object_when_schema_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", LLMProvider.OPENAI.value)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeChoice:
        def __init__(self, content: str) -> None:
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content: str) -> None:
            self.choices = [FakeChoice(content)]

    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            response_format = kwargs.get("response_format")
            if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
                raise Exception(
                    "Invalid schema for response_format 'classification': missing required keys"
                )
            return FakeResponse('{"requirements": []}')

    class FakeChat:
        def __init__(self) -> None:
            self.completions = FakeCompletions()

    class FakeOpenAIClient:
        def __init__(self, api_key: str | None) -> None:
            self.api_key = api_key
            self.chat = FakeChat()

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeOpenAIClient)

    client = LLMClient()
    result = await client.complete(
        "test prompt",
        output_schema={"type": "object", "properties": {}},
        schema_name="classification",
        stage_name="classification",
    )

    assert result == '{"requirements": []}'
    calls = client._openai_client.chat.completions.calls
    assert len(calls) == 2
    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[1]["response_format"]["type"] == "json_object"
