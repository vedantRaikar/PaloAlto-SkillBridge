"""Tests for app/api/routes/jobs.py."""
import json
import pytest
from pathlib import Path
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

import app.api.routes.jobs as jobs_module


def _make_extraction_result(success=True, skills=None):
    from app.models.graph import ExtractionResult, Node, Link
    skills = skills or ["python", "docker"]
    nodes = [Node(id=s, type="skill", category="programming") for s in skills]
    return ExtractionResult(nodes=nodes, links=[], success=success, method="heuristic")


@pytest.fixture()
def fake_pipeline(monkeypatch):
    pipeline = MagicMock()
    pipeline.extract = AsyncMock(return_value={
        "extraction_result": _make_extraction_result(True, ["python"]),
    })
    monkeypatch.setattr(jobs_module, "ExtractionPipeline", lambda **kwargs: pipeline)
    return pipeline


@pytest.fixture()
def fake_gm(monkeypatch):
    gm = MagicMock()
    gm.node_exists.return_value = False
    gm.graph = MagicMock()
    gm.graph.has_edge.return_value = False
    gm.graph.out_edges.return_value = []
    gm.graph.nodes = MagicMock()
    gm.graph.nodes.__getitem__ = MagicMock(return_value={"type": "skill"})
    gm.get_all_roles.return_value = [{"id": "role1", "title": "Role 1"}]
    gm.get_all_skills.return_value = [{"id": "skill1"}]
    gm.save_graph.return_value = None
    gm.add_node.return_value = None
    gm.add_edge.return_value = None
    gm.remove_edge.return_value = None
    monkeypatch.setattr(jobs_module, "GraphManager", lambda: gm)
    return gm


@pytest.fixture()
def jobs_file(tmp_path):
    """Write an empty jobs file to tmp_path and patch the storage dir."""
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text("[]")
    return jobs_path


@pytest.fixture()
def client(fake_pipeline, fake_gm, monkeypatch, tmp_path):
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text("[]")
    # Patch load/save to use the temp file
    monkeypatch.setattr(jobs_module, "load_jobs", lambda: json.loads(jobs_path.read_text()))
    monkeypatch.setattr(
        jobs_module, "save_jobs",
        lambda jobs: jobs_path.write_text(json.dumps(jobs))
    )
    app = FastAPI()
    app.include_router(jobs_module.router)
    return TestClient(app), jobs_path


# ---------------------------------------------------------------------------
# POST /ingest-role-batch
# ---------------------------------------------------------------------------

def test_ingest_role_batch_success(client, fake_pipeline):
    tc, _ = client
    response = tc.post("/ingest-role-batch", json={
        "role_name": "Python Engineer",
        "job_descriptions": [
            "We need Python and Docker skills",
            "Python is required with AWS",
        ],
        "min_frequency": 1,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["role_name"] == "Python Engineer"
    assert "selected_skills" in body


def test_ingest_role_batch_too_few_descriptions(client):
    tc, _ = client
    response = tc.post("/ingest-role-batch", json={
        "role_name": "Dev",
        "job_descriptions": ["Only one description"],
        "min_frequency": 1,
    })
    assert response.status_code == 422


def test_ingest_role_batch_no_skills_extracted(client, fake_pipeline):
    tc, _ = client
    fake_pipeline.extract.return_value = {
        "extraction_result": _make_extraction_result(success=False),
    }
    response = tc.post("/ingest-role-batch", json={
        "role_name": "Manager",
        "job_descriptions": ["Needs communication", "Leadership skills"],
        "min_frequency": 1,
    })
    assert response.status_code == 422


def test_ingest_role_batch_min_frequency_filters(client, fake_pipeline):
    tc, _ = client
    # Only 1 posting matches, but min_frequency=2 means it's filtered out
    fake_pipeline.extract.side_effect = [
        {"extraction_result": _make_extraction_result(True, ["python"])},
        {"extraction_result": _make_extraction_result(True, ["docker"])},
    ]
    response = tc.post("/ingest-role-batch", json={
        "role_name": "Mixed",
        "job_descriptions": ["Python needed", "Docker needed"],
        "min_frequency": 2,
    })
    assert response.status_code == 422


def test_ingest_role_batch_updates_existing_role(client, fake_pipeline, fake_gm):
    tc, _ = client
    fake_gm.node_exists.return_value = True  # role already exists
    fake_gm.graph.out_edges.return_value = []
    fake_gm.graph.nodes.__getitem__ = MagicMock(return_value={"type": "skill"})
    response = tc.post("/ingest-role-batch", json={
        "role_name": "Python Engineer",
        "job_descriptions": ["Python required", "Python developer needed"],
        "min_frequency": 1,
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_list_jobs_empty(client):
    tc, jobs_path = client
    response = tc.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["jobs"] == []
    assert body["total"] == 0


def test_list_jobs_with_data(client, monkeypatch):
    tc, jobs_path = client
    # Write a job to the file
    jobs = [{"job_id": "job_abc123456789", "data": {"title": "Dev"}}]
    jobs_path.write_text(json.dumps(jobs))
    response = tc.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1


def test_list_jobs_pagination(client):
    tc, jobs_path = client
    jobs = [{"job_id": f"job_{i:012x}", "data": {}} for i in range(5)]
    jobs_path.write_text(json.dumps(jobs))
    response = tc.get("/?limit=2&offset=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 2


# ---------------------------------------------------------------------------
# GET /{job_id}
# ---------------------------------------------------------------------------

def test_get_job_found(client):
    tc, jobs_path = client
    jobs = [{"job_id": "job_aaa000000001", "data": {"title": "Python Dev"}}]
    jobs_path.write_text(json.dumps(jobs))
    response = tc.get("/job_aaa000000001")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job_aaa000000001"


def test_get_job_not_found(client):
    tc, _ = client
    response = tc.get("/job_nonexistent_xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /{job_id}
# ---------------------------------------------------------------------------

def test_delete_job_found(client):
    tc, jobs_path = client
    jobs = [{"job_id": "job_del000000001", "data": {}}]
    jobs_path.write_text(json.dumps(jobs))
    response = tc.delete("/job_del000000001")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True


def test_delete_job_not_found(client):
    tc, _ = client
    response = tc.delete("/job_nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------

def test_get_discovered_roles(client, fake_gm):
    tc, _ = client
    response = tc.get("/roles")
    assert response.status_code == 200
    body = response.json()
    assert "roles" in body
    assert "total" in body


# ---------------------------------------------------------------------------
# GET /skills
# ---------------------------------------------------------------------------

def test_get_discovered_skills(client, fake_gm):
    tc, _ = client
    response = tc.get("/skills")
    assert response.status_code == 200
    body = response.json()
    assert "skills" in body


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

def test_get_job_stats_empty(client):
    tc, _ = client
    response = tc.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)


def test_get_job_stats_with_data(client):
    tc, jobs_path = client
    jobs = [{
        "job_id": "j1",
        "data": {
            "company": "Acme",
            "location": "NYC",
            "experience_level": "senior",
            "skills": ["python", "docker"],
        },
        "extraction_result": {"method_used": "heuristic"},
    }]
    jobs_path.write_text(json.dumps(jobs))
    response = tc.get("/stats")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# normalize_id helper
# ---------------------------------------------------------------------------

def test_normalize_id():
    from app.api.routes.jobs import normalize_id
    assert normalize_id("Python Developer") == "python_developer"
    assert normalize_id("  Full Stack   ") == "full_stack"
    assert normalize_id("C++ Engineer!") == "c_engineer"
