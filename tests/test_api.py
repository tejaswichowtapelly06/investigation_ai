import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.api.routes as routes


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_investigate_rejects_empty_question(client):
    resp = client.post("/investigate", json={"question": "   "})
    assert resp.status_code == 400


def test_investigate_rejects_missing_question(client):
    resp = client.post("/investigate", json={})
    assert resp.status_code == 400


def test_investigate_happy_path(client, monkeypatch):
    fake_state = {
        "final_answer": "The latency spike was associated with deployment v2.8.1 (INC-1042, DEP-882).",
        "confidence": "medium",
        "evidence": [
            {
                "document_id": "INC-1042",
                "title": "Order API latency spike",
                "type": "incident_report",
                "date": "2026-09-16",
                "version": "v2.8.1",
                "content": "P95 latency increased...",
            }
        ],
        "contradictions": [],
        "investigation_steps": ["Parsed question.", "Searched documents.", "Generated final answer."],
    }

    monkeypatch.setattr(routes, "run_investigation", lambda question: fake_state)

    resp = client.post("/investigate", json={"question": "Why did the Order API become slow?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == fake_state["final_answer"]
    assert body["confidence"] == "medium"
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["document_id"] == "INC-1042"
    assert body["trace"] == fake_state["investigation_steps"]


def test_investigate_returns_500_on_internal_error(client, monkeypatch):
    def boom(question):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(routes, "run_investigation", boom)

    resp = client.post("/investigate", json={"question": "anything"})
    assert resp.status_code == 500
    assert "internal error" in resp.json()["detail"].lower()
