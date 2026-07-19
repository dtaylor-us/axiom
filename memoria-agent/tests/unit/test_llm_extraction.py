"""Tests for LLM extraction in the distillation pipeline."""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.contracts import DistillRequest, MemoryCandidate
from app.pipeline.distiller import (
    MAX_SESSION_TEXT_CHARS,
    _build_session_text,
    _merge_candidates,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _candidate(content: str, memory_type: str = "DECISION") -> MemoryCandidate:
    return MemoryCandidate(
        memory_type=memory_type,
        content=content,
        rationale="Test rationale.",
        confidence="MEDIUM",
        source_excerpt=None,
        tags=[],
    )


def _request(summary: str = "", payload: dict | None = None) -> DistillRequest:
    return DistillRequest(
        session_id="test-session",
        project_id="test-project",
        pillar="ARCHON",
        session_summary=summary,
        session_payload=payload or {},
        existing_entries=[],
    )


# ---------------------------------------------------------------------------
# LLM gating tests — no API call expected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_extract_returns_empty_on_short_text(monkeypatch):
    """Text shorter than 200 chars must skip LLM extraction entirely."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    req = _request(summary="Short text.")

    # Patch get_llm_client so we can verify it is NOT called.
    with patch("app.pipeline.distiller.get_llm_client") as mock_client:
        from app.pipeline.distiller import distill
        result = await distill(req)

    mock_client.assert_not_called()
    # The message should show 0 LLM candidates.
    assert "0 LLM candidates" in result.message


@pytest.mark.asyncio
async def test_llm_extract_skips_when_no_api_key(monkeypatch):
    """LLM extraction must be skipped when OPENAI_API_KEY is not set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    long_text = "x " * 200
    req = _request(summary=long_text)

    with patch("app.pipeline.distiller.get_llm_client") as mock_client:
        from app.pipeline.distiller import distill
        result = await distill(req)

    mock_client.assert_not_called()
    assert "0 LLM candidates" in result.message


@pytest.mark.asyncio
async def test_llm_extract_falls_back_on_llm_failure(monkeypatch):
    """An LLM exception must be caught and distillation must still complete."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    long_text = "The team decided to use Kafka for event streaming. " * 10

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    with patch("app.pipeline.distiller.get_llm_client", return_value=mock_llm):
        from app.pipeline.distiller import distill
        result = await distill(_request(summary=long_text))

    # Must still return a valid response — not propagate the exception.
    assert result.session_id == "test-session"
    assert "0 LLM candidates" in result.message


# ---------------------------------------------------------------------------
# _merge_candidates tests
# ---------------------------------------------------------------------------

def test_merge_candidates_deduplicates_high_overlap():
    """LLM candidate with >= 0.70 token overlap with a deterministic one is excluded."""
    det = [_candidate("PostgreSQL is used as the primary database for the order service.")]
    # Nearly identical content — should be filtered out.
    llm = [_candidate("PostgreSQL is used as the primary database for the order service platform.")]
    merged = _merge_candidates(det, llm)
    assert len(merged) == 1
    assert merged[0].content == det[0].content


def test_merge_candidates_includes_distinct_llm_candidates():
    """LLM candidate with < 0.70 token overlap with deterministic entries is kept."""
    det = [_candidate("PostgreSQL is used as the primary database.")]
    llm = [_candidate("Redis is deployed for distributed session caching.")]
    merged = _merge_candidates(det, llm)
    assert len(merged) == 2


def test_merge_candidates_empty_llm_returns_deterministic():
    det = [_candidate("Some decision.")]
    merged = _merge_candidates(det, [])
    assert merged == det


# ---------------------------------------------------------------------------
# _build_session_text tests
# ---------------------------------------------------------------------------

def test_build_session_text_truncates_to_6000_chars():
    """Payload generating > 6000 chars of text must be truncated."""
    long_value = "architecture reasoning " * 300  # ~6900 chars
    req = _request(summary="", payload={"analysis": long_value})
    text = _build_session_text(req)
    assert len(text) <= MAX_SESSION_TEXT_CHARS


def test_build_session_text_skips_short_values():
    """Payload fields with string values <= 20 chars must be excluded from text."""
    req = _request(summary="", payload={"short": "hi", "uuid": "abc123"})
    text = _build_session_text(req)
    assert "hi" not in text
    assert "abc123" not in text


def test_build_session_text_includes_summary():
    summary = "The system must handle 10000 requests per second with sub-100ms latency."
    req = _request(summary=summary)
    text = _build_session_text(req)
    assert summary in text


def test_build_session_text_skips_uuid_strings():
    req = _request(summary="", payload={"id": "550e8400-e29b-41d4-a716-446655440000"})
    text = _build_session_text(req)
    assert "550e8400" not in text


# ---------------------------------------------------------------------------
# End-to-end pipeline test with mocked extractors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_distiller_pipeline_uses_both_extractors(monkeypatch):
    """Both extract_facts and _llm_extract must be called and candidates merged."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    long_summary = "The team chose PostgreSQL for ACID compliance reasons. " * 10

    det_candidate = _candidate("PostgreSQL chosen for ACID compliance.", "DECISION")
    llm_candidate = _candidate("Redis used for session cache.", "DECISION")

    llm_json = json.dumps(
        {
            "candidates": [
                {
                    "memory_type": "DECISION",
                    "content": llm_candidate.content,
                    "rationale": "LLM extracted.",
                    "confidence": "HIGH",
                    "source_excerpt": "Redis used",
                    "tags": ["redis"],
                }
            ]
        }
    )

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=llm_json)

    with (
        patch("app.pipeline.distiller.extract_facts", AsyncMock(return_value=[det_candidate])),
        patch("app.pipeline.distiller.get_llm_client", return_value=mock_llm),
        patch("app.pipeline.distiller.detect_conflicts", AsyncMock(return_value=[])),
    ):
        from app.pipeline.distiller import distill
        result = await distill(_request(summary=long_summary))

    # Both candidates should appear in the merged result.
    contents = [c.content for c in result.candidates]
    assert det_candidate.content in contents
    assert llm_candidate.content in contents
    assert "1 deterministic + 1 LLM candidates" in result.message
