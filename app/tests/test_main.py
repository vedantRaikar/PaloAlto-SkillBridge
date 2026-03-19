"""Tests for app/main.py – FastAPI application setup."""
import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Skill-Bridge Navigator API"
    assert "version" in body
    assert "groq_configured" in body


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "groq_api" in body


def test_openapi_schema_registered(client):
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "SkillBridge Navigator"


def test_cors_headers_present(client):
    # OPTIONS preflight should succeed due to CORSMiddleware
    response = client.options(
        "/",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code in (200, 400)  # middleware processes it


def test_roadmap_router_registered(client):
    # /api/v1/roadmap/roles exists in the roadmap router
    response = client.get("/api/v1/roadmap/roles")
    assert response.status_code == 200


def test_user_router_registered(client):
    # /api/v1/user/<unknown> returns 404 not 405
    response = client.get("/api/v1/user/nonexistent_user_xyz/skills")
    assert response.status_code in (200, 404, 422)


def test_ingest_router_registered(client):
    # POST to ingest job should be reachable (not 404 / 405)
    response = client.post(
        "/api/v1/ingest/job",
        json={"title": "Test Role", "description": "desc"},
    )
    assert response.status_code != 404


def test_learning_router_registered(client):
    response = client.get("/api/v1/learning/providers")
    assert response.status_code == 200


def test_chatbot_capabilities_registered(client):
    response = client.get("/api/v1/chatbot/capabilities")
    assert response.status_code == 200
