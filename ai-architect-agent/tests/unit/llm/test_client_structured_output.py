"""Tests for LLMClient structured output / schema enforcement.

Covers ADL-034: provider-native json_schema enforcement, ollama fallback,
and schema rejection fallback.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.llm.client import LLMClient, LLMCallException, _is_schema_rejection


SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
    },
    "required": ["result"],
}


class TestSchemaRejectionHeuristic:
    """Tests for the _is_schema_rejection() helper."""

    def test_returns_true_for_json_schema_keyword(self):
        exc = ValueError("json_schema type is not supported")
        assert _is_schema_rejection(exc) is True

    def test_returns_true_for_strict_keyword(self):
        exc = Exception("strict mode not available")
        assert _is_schema_rejection(exc) is True

    def test_returns_true_for_invalid_schema(self):
        exc = RuntimeError("invalid_schema provided")
        assert _is_schema_rejection(exc) is True

    def test_returns_false_for_unrelated_error(self):
        exc = ConnectionError("timed out")
        assert _is_schema_rejection(exc) is False

    def test_returns_false_for_empty_message(self):
        exc = ValueError("")
        assert _is_schema_rejection(exc) is False


@pytest.fixture()
def openai_client():
    """Return an LLMClient configured for openai with mocked ChatOpenAI."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LLM_PROVIDER": "openai"}):
        with patch("app.llm.client.ChatOpenAI") as mock_cls:
            mock_chat = MagicMock()
            mock_cls.return_value = mock_chat
            client = LLMClient()
            client._llm = mock_chat
            yield client, mock_chat


@pytest.fixture()
def ollama_client():
    """Return an LLMClient configured for ollama."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LLM_PROVIDER": "ollama"}):
        with patch("app.llm.client.ChatOpenAI") as mock_cls:
            mock_chat = MagicMock()
            mock_cls.return_value = mock_chat
            client = LLMClient()
            client._llm = mock_chat
            yield client, mock_chat


class TestStructuredOutputEnforcement:
    """Tests for schema enforcement in LLMClient.complete()."""

    async def test_json_schema_format_sent_to_openai(self, openai_client):
        """When output_schema provided + openai provider, json_schema type is used."""
        client, mock_chat = openai_client

        mock_bound = MagicMock()
        mock_chat.bind = MagicMock(return_value=mock_bound)
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_response.usage_metadata = {}
        mock_bound.ainvoke = AsyncMock(return_value=mock_response)

        await client.complete(
            "test prompt",
            response_format="json",
            output_schema=SAMPLE_SCHEMA,
            schema_name="test_stage",
        )

        bind_calls = mock_chat.bind.call_args_list
        assert len(bind_calls) == 1
        rf = bind_calls[0].kwargs.get("response_format") or bind_calls[0].args[0]
        if isinstance(rf, dict):
            assert rf.get("type") == "json_schema"
            assert rf["json_schema"]["name"] == "test_stage"
            assert rf["json_schema"]["strict"] is True
        else:
            # kwarg style
            assert bind_calls[0].kwargs.get("response_format", {}).get("type") == "json_schema"

    async def test_ollama_uses_json_object_fallback(self, ollama_client, caplog):
        """Ollama provider falls back to json_object and logs DEBUG."""
        import logging
        client, mock_chat = ollama_client

        mock_bound = MagicMock()
        mock_chat.bind = MagicMock(return_value=mock_bound)
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_response.usage_metadata = {}
        mock_bound.ainvoke = AsyncMock(return_value=mock_response)

        with caplog.at_level(logging.DEBUG, logger="app.llm.client"):
            await client.complete(
                "test prompt",
                response_format="json",
                output_schema=SAMPLE_SCHEMA,
                schema_name="test_stage",
            )

        bind_calls = mock_chat.bind.call_args_list
        assert len(bind_calls) == 1
        # The response_format must be json_object for ollama
        bound_rf = bind_calls[0].kwargs.get("response_format", {})
        assert bound_rf.get("type") == "json_object"

    async def test_schema_rejection_falls_back_to_json_object(self, openai_client, caplog):
        """When provider rejects strict schema, falls back to json_object + logs warning."""
        import logging
        client, mock_chat = openai_client

        rejection_exc = ValueError("json_schema strict mode not supported")
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_response.usage_metadata = {}

        # Patch _invoke directly to bypass tenacity's retry decorator.
        # This isolates complete()'s schema fallback logic from the retry mechanism.
        async def _mock_invoke(prompt, response_format_param=None):
            if response_format_param and response_format_param.get("type") == "json_schema":
                raise rejection_exc
            return mock_response

        with patch.object(client, "_invoke", side_effect=_mock_invoke):
            with caplog.at_level(logging.WARNING, logger="app.llm.client"):
                result = await client.complete(
                    "test prompt",
                    response_format="json",
                    output_schema=SAMPLE_SCHEMA,
                    schema_name="test_stage",
                )

        assert result == '{"result": "ok"}'
        assert any("schema_enforcement_fallback" in r.message for r in caplog.records) or \
               any("schema_enforcement_fallback" in str(r.__dict__) for r in caplog.records)

    async def test_no_schema_uses_json_object(self, openai_client):
        """When no output_schema is provided, json_object is used (legacy path)."""
        client, mock_chat = openai_client

        mock_bound = MagicMock()
        mock_chat.bind = MagicMock(return_value=mock_bound)
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_response.usage_metadata = {}
        mock_bound.ainvoke = AsyncMock(return_value=mock_response)

        await client.complete("test prompt", response_format="json")

        bind_calls = mock_chat.bind.call_args_list
        assert len(bind_calls) == 1
        bound_rf = bind_calls[0].kwargs.get("response_format", {})
        assert bound_rf.get("type") == "json_object"
