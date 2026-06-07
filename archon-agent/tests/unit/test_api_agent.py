"""Tests for app/api/agent.py — FastAPI route and helper functions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.agent import router, chunk, _stage_payload, AgentResponseChunk


# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------


class TestChunk:
    """Tests for the chunk() helper that produces NDJSON lines."""

    def test_chunk_returns_newline_terminated_json(self):
        result = chunk("TOKEN", content="hello")
        assert result.endswith("\n")
        data = json.loads(result.strip())
        assert data["type"] == "TOKEN"
        assert data["content"] == "hello"

    def test_chunk_excludes_none_fields(self):
        result = chunk("STAGE_COMPLETE", stage="parsing")
        data = json.loads(result.strip())
        assert "content" not in data
        assert data["stage"] == "parsing"

    def test_chunk_with_payload(self):
        result = chunk("STAGE_COMPLETE", stage="review", payload={"score": 90})
        data = json.loads(result.strip())
        assert data["payload"] == {"score": 90}

    def test_chunk_with_all_optional_fields(self):
        result = chunk(
            "TOOL_CALL",
            content="calling tool",
            stage="tools",
            toolName="requirement_parser",
            conversationId="abc-123",
            metadata={"tokens": 42},
        )
        data = json.loads(result.strip())
        assert data["toolName"] == "requirement_parser"
        assert data["conversationId"] == "abc-123"
        assert data["metadata"]["tokens"] == 42


class TestStagePayload:
    """Tests for the _stage_payload() helper."""

    def test_returns_dict_with_status_and_stage(self):
        result = _stage_payload("parsing")
        assert result["status"] == "complete"
        assert result["stage"] == "parsing"

    def test_extra_kwargs_included(self):
        result = _stage_payload("review", score=85, findings_count=3)
        assert result["score"] == 85
        assert result["findings_count"] == 3


# ---------------------------------------------------------------------------
# Integration tests for the /agent/stream endpoint
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_client():
    """Create a minimal FastAPI test app with the agent router."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Attach a dummy memory_store on app.state
    class _FakeState:
        memory_store = None

    test_app.state = _FakeState()

    return TestClient(test_app, raise_server_exceptions=True)


class TestAgentStreamEndpoint:
    """Tests for POST /agent/stream."""

    def test_unauthorized_missing_secret(self, app_client: TestClient):
        response = app_client.post(
            "/agent/stream",
            json={
                "conversationId": "c1",
                "userMessage": "Design a system",
            },
        )
        assert response.status_code == 401

    def test_unauthorized_wrong_secret(self, app_client: TestClient, monkeypatch):
        monkeypatch.setenv("INTERNAL_SECRET", "correct-secret")
        response = app_client.post(
            "/agent/stream",
            json={
                "conversationId": "c1",
                "userMessage": "Design a system",
            },
            headers={"x-internal-secret": "wrong-secret"},
        )
        assert response.status_code == 401

    def test_authorized_returns_streaming_response(
        self, app_client: TestClient, monkeypatch
    ):
        monkeypatch.setenv("INTERNAL_SECRET", "test-secret")

        async def _fake_pipeline(ctx, memory_store=None):
            yield chunk("TOKEN", content="hi")

        with patch("app.api.agent.run_pipeline", side_effect=_fake_pipeline):
            response = app_client.post(
                "/agent/stream",
                json={
                    "conversationId": "conv-abc",
                    "userMessage": "Build a payments platform",
                    "mode": "AUTO",
                    "history": [{"role": "USER", "content": "previous msg"}],
                },
                headers={"x-internal-secret": "test-secret"},
            )

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]
        assert response.headers["x-conversation-id"] == "conv-abc"

    def test_invalid_mode_falls_back_to_auto(
        self, app_client: TestClient, monkeypatch
    ):
        monkeypatch.setenv("INTERNAL_SECRET", "test-secret")
        captured: list = []

        async def _fake_pipeline(ctx, memory_store=None):
            captured.append(ctx.mode)
            yield chunk("TOKEN", content="done")

        with patch("app.api.agent.run_pipeline", side_effect=_fake_pipeline):
            app_client.post(
                "/agent/stream",
                json={
                    "conversationId": "c2",
                    "userMessage": "req",
                    "mode": "INVALID_MODE",
                },
                headers={"x-internal-secret": "test-secret"},
            )

        from app.models import PipelineMode
        assert captured[0] == PipelineMode.AUTO

    def test_empty_history_is_accepted(
        self, app_client: TestClient, monkeypatch
    ):
        monkeypatch.setenv("INTERNAL_SECRET", "test-secret")

        async def _fake_pipeline(ctx, memory_store=None):
            yield chunk("TOKEN", content="ok")

        with patch("app.api.agent.run_pipeline", side_effect=_fake_pipeline):
            response = app_client.post(
                "/agent/stream",
                json={
                    "conversationId": "c3",
                    "userMessage": "request",
                },
                headers={"x-internal-secret": "test-secret"},
            )

        assert response.status_code == 200
