"""Tests for app/api/routes/ingestion.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock

import app.api.routes.ingestion as ingestion_module


@pytest.fixture()
def fake_gm():
    gm = MagicMock()
    gm.get_node.return_value = None
    gm.save_graph.return_value = None
    gm.add_node.return_value = None
    gm.add_edge.return_value = None
    return gm


@pytest.fixture()
def client(fake_gm, monkeypatch):
    monkeypatch.setattr(ingestion_module, "graph_manager", fake_gm)
    app = FastAPI()
    app.include_router(ingestion_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /job
# ---------------------------------------------------------------------------

def test_ingest_job_minimal(client, fake_gm):
    response = client.post("/job", json={
        "title": "Python Developer",
        "description": "Build APIs",
        "skills": [],
    })
    assert response.status_code == 200
    body = response.json()
    assert "role_id" in body
    assert body["skills_count"] == 0
    fake_gm.add_node.assert_called()
    fake_gm.save_graph.assert_called()


def test_ingest_job_with_new_skills(client, fake_gm):
    fake_gm.get_node.return_value = None  # skills don't exist yet
    response = client.post("/job", json={
        "title": "DevOps Engineer",
        "description": "Deploy systems",
        "skills": ["docker", "kubernetes"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["skills_count"] == 2


def test_ingest_job_with_existing_skills(client, fake_gm):
    fake_gm.get_node.return_value = {"id": "python"}  # skill already exists
    response = client.post("/job", json={
        "title": "Backend Dev",
        "description": "APIs",
        "skills": ["python"],
    })
    assert response.status_code == 200
    # Should not add a new skill node if it already exists
    # add_edge should still be called to link role→skill


def test_ingest_job_with_company_and_url(client, fake_gm):
    response = client.post("/job", json={
        "title": "Dev",
        "description": "desc",
        "company": "Acme",
        "url": "https://example.com",
        "skills": [],
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /course
# ---------------------------------------------------------------------------

def test_ingest_course_minimal(client, fake_gm):
    response = client.post("/course", json={
        "title": "Python Bootcamp",
        "provider": "Udemy",
        "skills_taught": [],
    })
    assert response.status_code == 200
    body = response.json()
    assert "course_id" in body


def test_ingest_course_with_skills(client, fake_gm):
    fake_gm.get_node.return_value = None
    response = client.post("/course", json={
        "title": "Docker Mastery",
        "provider": "Udemy",
        "url": "https://udemy.com/docker",
        "duration_hours": 12.5,
        "skills_taught": ["docker", "kubernetes"],
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /skill
# ---------------------------------------------------------------------------

def test_add_skill(client, fake_gm):
    response = client.post("/skill", json={
        "id": "graphql",
        "category": "api",
        "aliases": ["gql"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == "graphql"
    fake_gm.add_node.assert_called()
    fake_gm.save_graph.assert_called()


def test_add_skill_no_aliases(client, fake_gm):
    response = client.post("/skill", json={"id": "redis"})
    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == "redis"


# ---------------------------------------------------------------------------
# POST /link
# ---------------------------------------------------------------------------

def test_add_link_success(client, fake_gm):
    fake_gm.get_node.side_effect = lambda id: {"id": id}  # both nodes exist
    response = client.post("/link?source=python_dev&target=python&link_type=REQUIRES")
    assert response.status_code == 200


def test_add_link_source_missing(client, fake_gm):
    fake_gm.get_node.side_effect = [None, {"id": "python"}]  # source missing
    response = client.post("/link?source=role_xyz&target=python&link_type=REQUIRES")
    assert response.status_code == 404


def test_add_link_target_missing(client, fake_gm):
    fake_gm.get_node.side_effect = [{"id": "role"}, None]
    response = client.post("/link?source=role_xyz&target=gone_skill&link_type=REQUIRES")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# normalize_id helper (indirectly tested through ingest)
# ---------------------------------------------------------------------------

def test_normalize_id_used_in_ingest(client, fake_gm):
    response = client.post("/job", json={"title": "Full Stack Developer", "description": "d"})
    assert response.status_code == 200
    body = response.json()
    # Role ID should be lowercase with underscores
    assert body["role_id"] == "full_stack_developer"
