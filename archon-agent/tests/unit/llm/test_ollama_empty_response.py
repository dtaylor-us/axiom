"""Tests for Ollama empty-response handling and startup connectivity checks."""

from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.llm.client import LLMClient


@pytest.mark.asyncio
async def test_complete_ollama_raises_value_error_when_response_is_empty() -> None:
    """_complete_ollama raises ValueError when Ollama returns an empty string."""
    client = _ollama_client_with_response("")

    with pytest.raises(ValueError, match="empty response"):
        await client._complete_ollama("prompt", "json", None, "requirement_challenge")

    client._test_patcher.stop()


@pytest.mark.asyncio
async def test_complete_ollama_raises_value_error_when_response_is_whitespace() -> None:
    """_complete_ollama raises ValueError when Ollama returns whitespace."""
    client = _ollama_client_with_response("   \n")

    with pytest.raises(ValueError, match="empty response"):
        await client._complete_ollama("prompt", "json", None, "requirement_challenge")

    client._test_patcher.stop()


@pytest.mark.asyncio
async def test_complete_ollama_returns_content_when_response_is_non_empty() -> None:
    """_complete_ollama returns non-empty Ollama response content."""
    client = _ollama_client_with_response('{"ok": true}')

    result = await client._complete_ollama(
        "prompt", "json", None, "requirement_challenge"
    )
    client._test_patcher.stop()

    assert result == '{"ok": true}'


@pytest.mark.asyncio
async def test_check_connectivity_logs_warning_for_docker_service_name(caplog) -> None:
    """check_connectivity warns when base_url uses the Docker service name."""
    client = _ollama_client_with_tags(
        base_url="http://ollama:11434",
        models=["qwen3:14b", "qwen3:8b"],
    )

    with caplog.at_level(logging.WARNING):
        await client.check_connectivity()
    client._test_patcher.stop()

    assert "Docker service name" in caplog.text


@pytest.mark.asyncio
async def test_check_connectivity_logs_info_for_host_docker_internal(caplog) -> None:
    """check_connectivity logs success for the native macOS host route."""
    client = _ollama_client_with_tags(
        base_url="http://host.docker.internal:11434",
        models=["qwen3:14b", "qwen3:8b"],
    )

    with caplog.at_level(logging.INFO):
        await client.check_connectivity()
    client._test_patcher.stop()

    assert "OLLAMA_STARTUP: connected" in caplog.text
    assert "host.docker.internal" in caplog.text


@pytest.mark.asyncio
async def test_check_connectivity_logs_error_when_primary_model_is_missing(caplog) -> None:
    """check_connectivity logs an error when the primary model is unavailable."""
    client = _ollama_client_with_tags(
        base_url="http://host.docker.internal:11434",
        models=["qwen3:8b"],
    )

    with caplog.at_level(logging.ERROR):
        await client.check_connectivity()
    client._test_patcher.stop()

    assert "primary model 'qwen3:14b' not found" in caplog.text


@pytest.mark.asyncio
async def test_check_connectivity_handles_connection_refused_gracefully(caplog) -> None:
    """check_connectivity logs connection errors without raising."""
    client = _ollama_client_with_connection_error()

    with caplog.at_level(logging.ERROR):
        await client.check_connectivity()
    client._test_patcher.stop()

    assert "cannot reach Ollama" in caplog.text


def _base_ollama_client(base_url: str = "http://host.docker.internal:11434") -> LLMClient:
    """Create an Ollama client with deterministic native-host configuration."""
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": base_url,
            "OLLAMA_PRIMARY_MODEL": "qwen3:14b",
            "OLLAMA_FAST_MODEL": "qwen3:8b",
        },
        clear=False,
    ):
        return LLMClient()


def _ollama_client_with_response(content: str) -> LLMClient:
    """Create an Ollama client whose generate call returns content."""
    client = _base_ollama_client()

    class AsyncClientStub:
        """Minimal async httpx client stub for generate responses."""

        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self) -> "AsyncClientStub":
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, json: dict) -> MagicMock:
            response = MagicMock()
            response.json.return_value = {"response": content}
            response.raise_for_status.return_value = None
            return response

    patcher = patch("app.llm.client.httpx.AsyncClient", AsyncClientStub)
    client._test_patcher = patcher
    patcher.start()
    return client


def _ollama_client_with_tags(base_url: str, models: list[str]) -> LLMClient:
    """Create an Ollama client whose tags call returns models."""
    client = _base_ollama_client(base_url)

    class AsyncClientStub:
        """Minimal async httpx client stub for tags responses."""

        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self) -> "AsyncClientStub":
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def get(self, url: str) -> MagicMock:
            response = MagicMock()
            response.json.return_value = {
                "models": [{"name": model} for model in models]
            }
            response.raise_for_status.return_value = None
            return response

    patcher = patch("app.llm.client.httpx.AsyncClient", AsyncClientStub)
    client._test_patcher = patcher
    patcher.start()
    return client


def _ollama_client_with_connection_error() -> LLMClient:
    """Create an Ollama client whose tags call raises ConnectError."""
    client = _base_ollama_client()

    class AsyncClientStub:
        """Minimal async httpx client stub for connection failures."""

        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self) -> "AsyncClientStub":
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def get(self, url: str) -> MagicMock:
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("connection refused", request=request)

    patcher = patch("app.llm.client.httpx.AsyncClient", AsyncClientStub)
    client._test_patcher = patcher
    patcher.start()
    return client
