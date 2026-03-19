"""Tests for app/api/routes/profile.py."""
import io
import pytest
import networkx as nx
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

import app.api.routes.profile as profile_module
from app.models.profile import UserProfile, ProfileSource, ContactInfo


def _make_user_profile(uid="user1", name="Alice", skills=None):
    return UserProfile(
        id=uid,
        name=name,
        sources=[ProfileSource.GITHUB],
        skills=skills or ["python", "docker"],
        contact=ContactInfo(email="alice@example.com", github="alice"),
    )


@pytest.fixture()
def fake_pb(monkeypatch):
    pb = MagicMock()
    pb.build_from_github_async = AsyncMock(return_value=_make_user_profile())
    pb.build_from_resume = MagicMock(return_value=_make_user_profile())
    pb.merge_profiles = MagicMock(return_value=_make_user_profile())
    pb.save_to_graph = MagicMock()
    pb.calculate_readiness = MagicMock(return_value={"role1": 0.75})
    pb.clear_github_cache = MagicMock()
    monkeypatch.setattr(profile_module, "profile_builder", pb)
    return pb


@pytest.fixture()
def fake_gm(monkeypatch):
    gm = MagicMock()
    gm.get_node = MagicMock(return_value={"type": "user", "title": "Alice", "metadata": {}})
    gm.get_user_skills = MagicMock(return_value=["python", "docker"])
    gm.get_all_roles = MagicMock(return_value=[{"id": "role1"}])
    gm.node_exists = MagicMock(return_value=False)
    gm.add_node = MagicMock()
    gm.add_edge = MagicMock()
    gm.remove_edge = MagicMock()
    gm.save_graph = MagicMock()
    gm.graph = nx.DiGraph()
    gm.graph.add_node("user1", type="user", title="Alice", metadata={})
    gm.graph.add_node("python", type="skill", title="Python")
    gm.graph.add_edge("user1", "python", type="has_skill")
    monkeypatch.setattr(profile_module, "graph_manager", gm)
    return gm


@pytest.fixture()
def client(fake_pb, fake_gm, monkeypatch, tmp_path):
    csv_path = tmp_path / "profiles.csv"
    monkeypatch.setattr(profile_module, "_get_profiles_csv_path", lambda: csv_path)
    app = FastAPI()
    app.include_router(profile_module.router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /cache/clear and GET /cache/status (simple endpoints)
# ---------------------------------------------------------------------------

def test_clear_cache(client, fake_pb):
    response = client.post("/cache/clear")
    assert response.status_code == 200
    assert response.json()["message"] == "Cache cleared successfully"
    fake_pb.clear_github_cache.assert_called_once()


def test_cache_status(client, monkeypatch):
    from app.services import github_analyzer
    class FakeCache:
        _cache = {"user1": "data", "user2": "data"}
    monkeypatch.setattr(profile_module, "profile_builder", profile_module.profile_builder)
    import app.services.github_analyzer as gha_mod
    old_cache = gha_mod.GitHubCache
    gha_mod.GitHubCache = FakeCache
    try:
        response = client.get("/cache/status")
        assert response.status_code == 200
        body = response.json()
        assert "cached_items" in body
    finally:
        gha_mod.GitHubCache = old_cache


# ---------------------------------------------------------------------------
# POST /github
# ---------------------------------------------------------------------------

def test_analyze_github_success(client, fake_pb):
    response = client.post("/github", json={"github_username": "alice"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user1"
    assert "python" in body["skills"]


def test_analyze_github_not_found(client, fake_pb):
    fake_pb.build_from_github_async.return_value = None
    response = client.post("/github", json={"github_username": "nonexistent"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /resume
# ---------------------------------------------------------------------------

def test_upload_resume_pdf_success(client, fake_pb):
    content = b"%PDF-1.4 fake pdf content"
    response = client.post(
        "/resume",
        files={"file": ("resume.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user1"


def test_upload_resume_unsupported_type(client):
    content = b"plain text resume"
    response = client.post(
        "/resume",
        files={"file": ("resume.txt", io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_resume_parse_error(client, fake_pb):
    fake_pb.build_from_resume.side_effect = ValueError("Cannot parse file")
    content = b"%PDF-1.4 bad content"
    response = client.post(
        "/resume",
        files={"file": ("resume.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_resume_docx(client):
    content = b"PK fake docx content"
    response = client.post(
        "/resume",
        files={"file": ("cv.docx", io.BytesIO(content), "application/octet-stream")},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /merge
# ---------------------------------------------------------------------------

def test_merge_profiles_github_only(client, fake_pb):
    response = client.post("/merge", json={
        "user_id": "user_merged",
        "github_username": "alice",
    })
    assert response.status_code == 200


def test_merge_profiles_manual_skills_only(client, fake_pb):
    response = client.post("/merge", json={
        "user_id": "user_manual",
        "additional_skills": ["python", "aws"],
    })
    assert response.status_code == 200


def test_merge_profiles_no_data(client, fake_pb):
    response = client.post("/merge", json={"user_id": "user_empty"})
    assert response.status_code == 400


def test_merge_profiles_both_sources(client, fake_pb):
    import base64
    fake_content = base64.b64encode(b"%PDF-1.4 resume content").decode()
    response = client.post("/merge", json={
        "user_id": "user_full",
        "github_username": "alice",
        "resume_base64": fake_content,
        "resume_filename": "resume.pdf",
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /manual
# ---------------------------------------------------------------------------

def test_create_manual_profile_basic(client):
    response = client.post("/manual", json={
        "user_id": "manual_u1",
        "name": "Bob",
        "skills": ["java", "spring"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Bob"


def test_create_manual_profile_with_github(client, fake_pb):
    response = client.post("/manual", json={
        "user_id": "manual_u2",
        "name": "Carol",
        "github_username": "carol",
        "email": "carol@example.com",
        "skills": [],
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /cache/status (already tested above)
# GET /{user_id}
# ---------------------------------------------------------------------------

def test_get_profile_found(client, fake_gm):
    response = client.get("/user1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user1"


def test_get_profile_not_found(client, fake_gm):
    fake_gm.get_node.return_value = None
    response = client.get("/nonexistent_user")
    assert response.status_code == 404


def test_get_profile_wrong_type(client, fake_gm):
    fake_gm.get_node.return_value = {"type": "skill", "title": "Python"}
    response = client.get("/python_skill")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /{user_id}/graph
# ---------------------------------------------------------------------------

def test_get_user_graph(client, fake_gm):
    response = client.get("/user1/graph")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user1"
    assert "nodes" in body
    assert "edges" in body


def test_get_user_graph_not_found(client, fake_gm):
    fake_gm.get_node.return_value = None
    response = client.get("/ghost_user/graph")
    assert response.status_code == 404


def test_get_user_graph_invalid_depth(client):
    response = client.get("/user1/graph?depth=10")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /{user_id}
# ---------------------------------------------------------------------------

def test_update_profile_name(client, fake_gm):
    fake_gm.graph.nodes = {"user1": {"type": "user", "title": "Alice", "metadata": {}}}
    response = client.patch("/user1", json={"name": "Alice Updated"})
    assert response.status_code == 200


def test_update_profile_no_fields(client, fake_gm):
    response = client.patch("/user1", json={})
    assert response.status_code == 400


def test_update_profile_not_found(client, fake_gm):
    fake_gm.get_node.return_value = None
    response = client.patch("/ghost", json={"name": "Ghost"})
    assert response.status_code == 404


def test_update_profile_with_skills(client, fake_gm):
    fake_gm.graph.nodes = {"user1": {"type": "user", "title": "Alice", "metadata": {}}}
    fake_gm.graph.out_edges = MagicMock(return_value=[])
    response = client.patch("/user1", json={"skills": ["python", "docker"]})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/readiness
# ---------------------------------------------------------------------------

def test_get_readiness(client, fake_gm, fake_pb):
    response = client.get("/user1/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user1"
    assert "readiness_scores" in body


def test_get_readiness_not_found(client, fake_gm):
    fake_gm.get_node.return_value = None
    response = client.get("/ghost/readiness")
    assert response.status_code == 404
