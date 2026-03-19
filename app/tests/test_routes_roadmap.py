"""Tests for app/api/routes/roadmap.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock

import app.api.routes.roadmap as roadmap_module


@pytest.fixture()
def fake_gm():
    gm = MagicMock()
    gm.get_all_roles.return_value = [
        {"id": "backend_developer", "title": "Backend Developer"},
        {"id": "devops_engineer", "title": "DevOps Engineer"},
    ]
    gm.get_all_skills.return_value = [
        {"id": "python"}, {"id": "docker"}, {"id": "kubernetes"}
    ]
    gm.graph = MagicMock()
    gm.graph.nodes.return_value = []
    gm.graph.nodes.__iter__ = MagicMock(return_value=iter([]))
    gm.get_graph_stats.return_value = {"nodes": 10, "edges": 20}
    return gm


@pytest.fixture()
def fake_gap_analyzer():
    ga = MagicMock()
    ga.analyze_gaps.return_value = MagicMock(
        missing_skills=["docker", "kubernetes"],
        matched_skills=["python"],
        courses_for_gaps={},
    )
    ga.calculate_readiness_score.return_value = 0.6
    ga.get_ordered_learning_path.return_value = {"phases": [], "total_skills": 2}
    ga.get_fast_track_path.return_value = {"skills": [], "timeline_weeks": 4}
    ga.get_optimized_paths.return_value = {"fastest": [], "most_impactful": []}
    ga.get_role_requirements.return_value = {"required_skills": ["docker"]}
    return ga


@pytest.fixture()
def fake_roadmap_generator():
    rg = MagicMock()
    from app.models.user import Roadmap
    rg.generate_structured_roadmap.return_value = Roadmap(
        user_id="u1",
        target_role="backend_developer",
        total_weeks=2,
        weeks=[],
        ai_generated=False,
        fallback_used=True,
    )
    return rg


@pytest.fixture()
def client(fake_gm, fake_gap_analyzer, fake_roadmap_generator, monkeypatch):
    monkeypatch.setattr(roadmap_module, "graph_manager", fake_gm)
    monkeypatch.setattr(roadmap_module, "gap_analyzer", fake_gap_analyzer)
    monkeypatch.setattr(roadmap_module, "roadmap_generator", fake_roadmap_generator)
    app = FastAPI()
    app.include_router(roadmap_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------

def test_get_roles(client, fake_gm):
    response = client.get("/roles")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["roles"], list)
    assert any(r["id"] == "backend_developer" for r in body["roles"])


# ---------------------------------------------------------------------------
# GET /skills
# ---------------------------------------------------------------------------

def test_get_skills(client, fake_gm):
    response = client.get("/skills")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["skills"], list)


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------

def test_get_graph_data_empty(client, fake_gm):
    fake_gm.graph.nodes.return_value = []
    # Override nodes() to be iterable
    class FakeNodes:
        def __iter__(self): return iter([])
        def __call__(self): return self
    fake_gm.graph.nodes = FakeNodes()
    response = client.get("/graph")
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "edges" in body
    assert "stats" in body


def test_get_graph_data_with_type_filter(client, fake_gm):
    class FakeNodes:
        def __iter__(self): return iter([])
        def __call__(self): return self
    fake_gm.graph.nodes = FakeNodes()
    response = client.get("/graph?type=skill")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/gap-analysis
# ---------------------------------------------------------------------------

def test_get_gap_analysis(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/gap-analysis")
    assert response.status_code == 200
    body = response.json()
    assert "gap_analysis" in body
    assert "readiness_score" in body


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/roadmap
# ---------------------------------------------------------------------------

def test_get_roadmap(client, fake_roadmap_generator):
    response = client.get("/u1/backend_developer/roadmap")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/learning-path
# ---------------------------------------------------------------------------

def test_get_learning_path(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/learning-path")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/fast-track
# ---------------------------------------------------------------------------

def test_get_fast_track(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/fast-track")
    assert response.status_code == 200


def test_get_fast_track_custom_max_skills(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/fast-track?max_skills=3")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/optimized-paths
# ---------------------------------------------------------------------------

def test_get_optimized_paths(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/optimized-paths")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /{user_id}/{target_role}/requirements
# ---------------------------------------------------------------------------

def test_get_role_requirements(client, fake_gap_analyzer):
    response = client.get("/u1/backend_developer/requirements")
    assert response.status_code == 200
    body = response.json()
    assert "requirements" in body or "required_skills" in body or "readiness_score" in body
