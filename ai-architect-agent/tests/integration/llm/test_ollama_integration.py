"""Integration tests for local Ollama structured output."""

from __future__ import annotations

import json
import os

import httpx
import pytest

from app.llm.client import LLMClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LLM_PROVIDER") != "ollama",
        reason="Ollama integration tests require LLM_PROVIDER=ollama",
    ),
]

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "score": {"type": "integer"},
    },
    "required": ["name", "score"],
}


@pytest.mark.asyncio
async def test_ollama_is_reachable_at_configured_base_url() -> None:
    """Ollama responds to the tags endpoint."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{base_url}/api/tags")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ollama_has_configured_primary_model_available() -> None:
    """The configured primary model appears in Ollama tags."""
    models = await _ollama_model_names()

    assert os.getenv("OLLAMA_PRIMARY_MODEL", "qwen3:14b") in models


@pytest.mark.asyncio
async def test_ollama_has_configured_fast_model_available() -> None:
    """The configured fast model appears in Ollama tags."""
    models = await _ollama_model_names()

    assert os.getenv("OLLAMA_FAST_MODEL", "qwen3:8b") in models


@pytest.mark.asyncio
async def test_complete_returns_valid_json_when_schema_provided() -> None:
    """LLMClient returns parseable JSON under Ollama schema format."""
    client = LLMClient()

    raw = await client.complete(
        "Return name as 'test' and score as 42.",
        output_schema=SAMPLE_SCHEMA,
        schema_name="sample",
        stage_name="requirement_parsing",
    )

    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_structured_output_matches_schema_shape() -> None:
    """Ollama structured output includes the required schema fields."""
    client = LLMClient()

    raw = await client.complete(
        "Return name as 'test' and score as 42.",
        output_schema=SAMPLE_SCHEMA,
        schema_name="sample",
        stage_name="requirement_parsing",
    )

    parsed = json.loads(raw)
    assert isinstance(parsed["name"], str)
    assert isinstance(parsed["score"], int)


async def _ollama_model_names() -> set[str]:
    """Return model names reported by the local Ollama server."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{base_url}/api/tags")
    response.raise_for_status()
    return {model["name"] for model in response.json().get("models", [])}
