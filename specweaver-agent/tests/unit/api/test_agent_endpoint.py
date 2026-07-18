"""Tests for the /agent/extract endpoint."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.contracts import ArchInputPackage


class SuccessfulGraph:
    def __init__(self, package):
        self.package = package
        self.context = None

    async def ainvoke(self, context):
        self.context = context
        context.arch_input_package = self.package
        return context


class FailingGraph:
    async def ainvoke(self, context):
        raise RuntimeError("pipeline boom")


def test_post_agent_extract_returns_200_on_success(monkeypatch, document, classified_set):
    package = _package(classified_set)
    monkeypatch.setattr("app.api.agent.build_graph", lambda llm: SuccessfulGraph(package))
    response = TestClient(app).post(
        "/agent/extract",
        json={"sessionId": "session-1", "documents": [document.model_dump(by_alias=True)]},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_post_agent_extract_returns_extraction_response_with_json(
    monkeypatch,
    document,
    classified_set,
):
    package = _package(classified_set)
    monkeypatch.setattr("app.api.agent.build_graph", lambda llm: SuccessfulGraph(package))
    response = TestClient(app).post(
        "/agent/extract",
        json={"sessionId": "session-1", "documents": [document.model_dump(by_alias=True)]},
    )
    body = response.json()
    assert json.loads(body["archInputPackageJson"])["sessionId"] == "session-1"


def test_post_agent_extract_accepts_project_memory_context(monkeypatch, document, classified_set):
    package = _package(classified_set)
    graph = SuccessfulGraph(package)
    monkeypatch.setattr("app.api.agent.build_graph", lambda llm: graph)
    response = TestClient(app).post(
        "/agent/extract",
        json={
            "sessionId": "session-1",
            "documents": [document.model_dump(by_alias=True)],
            "projectMemoryContext": {"requirements": [{"content": "Keep data in region"}]},
        },
    )
    assert response.status_code == 200
    assert graph.context.project_memory_context["requirements"][0]["content"] == "Keep data in region"


def test_post_agent_extract_returns_success_false_on_pipeline_error(
    monkeypatch,
    document,
):
    monkeypatch.setattr("app.api.agent.build_graph", lambda llm: FailingGraph())
    response = TestClient(app).post(
        "/agent/extract",
        json={"sessionId": "session-1", "documents": [document.model_dump(by_alias=True)]},
    )
    assert response.status_code == 200
    assert response.json()["success"] is False


def test_post_agent_extract_returns_error_message_on_failure(monkeypatch, document):
    monkeypatch.setattr("app.api.agent.build_graph", lambda llm: FailingGraph())
    response = TestClient(app).post(
        "/agent/extract",
        json={"sessionId": "session-1", "documents": [document.model_dump(by_alias=True)]},
    )
    assert "pipeline boom" in response.json()["errorMessage"]


def test_get_health_returns_200():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "specweaver-agent"


def _package(classified_set) -> ArchInputPackage:
    return ArchInputPackage(
        package_id="pkg-1",
        session_id="session-1",
        created_at="2026-05-30T00:00:00Z",
        system_description="A system.",
        requirements=classified_set.requirements,
        source_documents=[],
        total_requirements=1,
        high_confidence_count=1,
        inferred_count=0,
    )
