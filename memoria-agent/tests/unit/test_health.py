from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "memoria-agent"


def test_distill_requires_internal_secret():
    response = client.post("/distill", json={
        "session_id": "s1", "project_id": "p1", "pillar": "ARCHON"
    })
    assert response.status_code == 401


def test_distill_runs_phase_3_pipeline(monkeypatch):
    monkeypatch.setenv("INTERNAL_SECRET", "test-secret")
    response = client.post(
        "/distill",
        json={
            "session_id": "s1",
            "project_id": "p1",
            "pillar": "ARCHON",
            "session_summary": "Decision: Use PostgreSQL for order consistency.",
        },
        headers={"x-internal-secret": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["candidates"][0]["memory_type"] == "DECISION"
    assert response.json()["conflicts"] == []
