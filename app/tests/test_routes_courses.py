"""Tests for app/api/routes/courses.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

import app.api.routes.courses as courses_module


def _make_fake_course(title="Python Basics", provider="Coursera"):
    c = MagicMock()
    c.model_dump.return_value = {"title": title, "provider": provider, "url": "http://example.com"}
    return c


def _make_fake_cert(title="AWS SAA", provider="AWS"):
    c = MagicMock()
    c.model_dump.return_value = {"title": title, "provider": provider, "id": "aws_saa"}
    return c


@pytest.fixture()
def fake_lrm():
    lrm = MagicMock()

    search_resp = MagicMock()
    search_resp.courses = [_make_fake_course()]
    lrm.search_courses = AsyncMock(return_value=search_resp)

    discover_resp = MagicMock()
    lrm.discover_courses_for_skills = AsyncMock(return_value=discover_resp)

    lrm.get_learning_resources_for_skill.return_value = {
        "courses": [{"title": "Python Basics"}],
        "certifications": [],
    }
    lrm.get_graph_stats.return_value = {"nodes": 5}
    lrm.cached_courses = {}
    lrm.course_aggregator = MagicMock()
    lrm.course_aggregator.scrapers = {"coursera": MagicMock()}

    lrm.search_certifications.return_value = [_make_fake_cert()]
    lrm.recommend_certifications_for_skills.return_value = [
        {"title": "AWS SAA", "provider": "AWS"}
    ]
    return lrm


@pytest.fixture()
def fake_course_aggregator():
    ca = MagicMock()
    ca.scrapers = {"coursera": MagicMock(), "udemy": MagicMock()}
    return ca


@pytest.fixture()
def fake_cert_service():
    cs = MagicMock()
    cs.get_providers.return_value = [MagicMock(model_dump=lambda: {"name": "AWS"})]
    provider = MagicMock()
    provider.model_dump.return_value = {"name": "AWS"}
    cs.get_providers.return_value = [provider]
    cert = MagicMock()
    cert.model_dump.return_value = {"id": "cert1", "title": "AWS SAA"}
    cs.get_by_id.return_value = cert
    cs.get_career_path.return_value = []
    cs.get_prerequisites.return_value = []
    return cs


@pytest.fixture()
def client(fake_lrm, fake_course_aggregator, fake_cert_service, monkeypatch):
    monkeypatch.setattr(courses_module, "get_learning_resource_manager", lambda: fake_lrm)
    monkeypatch.setattr(courses_module, "get_course_aggregator", lambda: fake_course_aggregator)
    monkeypatch.setattr(courses_module, "get_certification_service", lambda: fake_cert_service)
    app = FastAPI()
    app.include_router(courses_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /search
# ---------------------------------------------------------------------------

def test_search_courses(client):
    response = client.post("/search", json={"skill": "python", "max_results": 5})
    assert response.status_code == 200


def test_search_courses_error(client, fake_lrm):
    fake_lrm.search_courses.side_effect = RuntimeError("DB error")
    response = client.post("/search", json={"skill": "python"})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /discover
# ---------------------------------------------------------------------------

def test_discover_courses(client):
    response = client.post("/discover", json={"skills": ["python", "docker"]})
    assert response.status_code == 200


def test_discover_courses_error(client, fake_lrm):
    fake_lrm.discover_courses_for_skills.side_effect = ValueError("bad input")
    response = client.post("/discover", json={"skills": ["python"]})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /for-skill/{skill_id}
# ---------------------------------------------------------------------------

def test_get_courses_for_skill(client):
    response = client.get("/for-skill/python")
    assert response.status_code == 200
    body = response.json()
    assert "courses" in body


def test_get_courses_for_skill_error(client, fake_lrm):
    fake_lrm.get_learning_resources_for_skill.side_effect = RuntimeError("fail")
    response = client.get("/for-skill/python")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /providers
# ---------------------------------------------------------------------------

def test_get_course_providers(client):
    response = client.get("/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body
    assert "coursera" in body["providers"]


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

def test_get_course_stats(client):
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert "course_stats" in body


def test_get_course_stats_error(client, fake_lrm):
    fake_lrm.get_graph_stats.side_effect = RuntimeError("fail")
    response = client.get("/stats")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /certifications/search
# ---------------------------------------------------------------------------

def test_search_certifications(client):
    response = client.get("/certifications/search?skill=aws")
    assert response.status_code == 200


def test_search_certifications_error(client, fake_lrm):
    fake_lrm.search_certifications.side_effect = RuntimeError("fail")
    response = client.get("/certifications/search")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /certifications/providers
# ---------------------------------------------------------------------------

def test_get_certification_providers(client):
    response = client.get("/certifications/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body


def test_get_certification_providers_error(client, fake_cert_service):
    fake_cert_service.get_providers.side_effect = RuntimeError("fail")
    response = client.get("/certifications/providers")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /certifications/{cert_id}
# ---------------------------------------------------------------------------

def test_get_certification_found(client):
    response = client.get("/certifications/cert1")
    assert response.status_code == 200
    body = response.json()
    assert "certification" in body


def test_get_certification_not_found(client, fake_cert_service):
    fake_cert_service.get_by_id.return_value = None
    response = client.get("/certifications/nonexistent")
    assert response.status_code == 404


def test_get_certification_error(client, fake_cert_service):
    fake_cert_service.get_by_id.side_effect = RuntimeError("fail")
    response = client.get("/certifications/cert1")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /certifications/recommend
# ---------------------------------------------------------------------------

def test_recommend_certifications(client):
    response = client.post("/certifications/recommend", json=["python", "aws"])
    assert response.status_code == 200
    body = response.json()
    assert "recommendations" in body
    assert "total" in body


def test_recommend_certifications_error(client, fake_lrm):
    fake_lrm.recommend_certifications_for_skills.side_effect = RuntimeError("fail")
    response = client.post("/certifications/recommend", json=["python"])
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /learning-paths
# ---------------------------------------------------------------------------

def test_generate_learning_paths(client):
    response = client.post("/learning-paths", json={
        "skills": ["python"],
        "include_certifications": True,
        "budget": "any",
    })
    assert response.status_code == 200
    body = response.json()
    assert "skills" in body
    assert "courses_by_skill" in body


def test_generate_learning_paths_no_certs(client):
    response = client.post("/learning-paths", json={
        "skills": ["docker"],
        "include_certifications": False,
        "budget": "free",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["certification_recommendations"] == []


def test_generate_learning_paths_error(client, fake_lrm):
    fake_lrm.recommend_certifications_for_skills.side_effect = RuntimeError("fail")
    response = client.post("/learning-paths", json={"skills": ["python"]})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /for-gap-analysis
# ---------------------------------------------------------------------------

def test_get_resources_for_gap(client):
    response = client.get("/for-gap-analysis?missing_skills=python,docker&matched_skills=git")
    assert response.status_code == 200
    body = response.json()
    assert "missing_skills" in body
    assert "matched_skills" in body
    assert "resources" in body
    assert "summary" in body


def test_get_resources_for_gap_empty(client):
    response = client.get("/for-gap-analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["missing_skills"] == []


def test_get_resources_for_gap_error(client, fake_lrm):
    fake_lrm.get_learning_resources_for_skill.side_effect = RuntimeError("fail")
    response = client.get("/for-gap-analysis?missing_skills=python")
    assert response.status_code == 500
