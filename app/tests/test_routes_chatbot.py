"""Tests for app/api/routes/chatbot.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock

import app.api.routes.chatbot as chatbot_module


@pytest.fixture()
def fake_chatbot():
    cb = MagicMock()
    cb.ask.return_value = {
        "answer": "You should learn Python.",
        "context_used": True,
        "intent": "skill_recommendation",
        "suggestions": ["Learn Django", "Try FastAPI"],
        "entities_found": {"skills": ["python"], "roles": []},
    }
    cb._get_suggestions.return_value = [
        "What skills do I need for backend development?",
        "How do I become a DevOps engineer?",
    ]
    return cb


@pytest.fixture()
def client(fake_chatbot, monkeypatch):
    monkeypatch.setattr(chatbot_module, "get_graph_rag_chatbot", lambda: fake_chatbot)
    app = FastAPI()
    app.include_router(chatbot_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

def test_chat_basic(client, fake_chatbot):
    response = client.post("/chat", json={
        "question": "What skills do I need?",
        "history": [],
        "selected_role": None,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You should learn Python."
    assert body["context_used"] is True
    assert body["intent"] == "skill_recommendation"
    assert "Learn Django" in body["suggestions"]


def test_chat_with_history(client, fake_chatbot):
    response = client.post("/chat", json={
        "question": "Continue from here",
        "history": [{"role": "user", "content": "Hello"}],
        "selected_role": "backend_developer",
    })
    assert response.status_code == 200
    # Verify history was passed through
    call_kwargs = fake_chatbot.ask.call_args
    assert call_kwargs is not None


def test_chat_with_assistant_history(client, fake_chatbot):
    response = client.post("/chat", json={
        "question": "Tell me more",
        "history": [
            {"role": "user", "content": "What is Docker?"},
            {"role": "assistant", "content": "Docker is a container platform."},
        ],
    })
    assert response.status_code == 200


def test_chat_service_error_returns_500(client, fake_chatbot):
    fake_chatbot.ask.side_effect = RuntimeError("LLM unavailable")
    response = client.post("/chat", json={"question": "Hello"})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /suggestions
# ---------------------------------------------------------------------------

def test_get_suggestions(client, fake_chatbot):
    response = client.get("/suggestions")
    assert response.status_code == 200
    body = response.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) == 2


def test_get_suggestions_error(client, fake_chatbot):
    fake_chatbot._get_suggestions.side_effect = RuntimeError("broken")
    response = client.get("/suggestions")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /capabilities
# ---------------------------------------------------------------------------

def test_get_capabilities(client):
    response = client.get("/capabilities")
    assert response.status_code == 200
    body = response.json()
    # Should have some content
    assert isinstance(body, dict)
    assert len(body) > 0
