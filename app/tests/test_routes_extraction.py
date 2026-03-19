"""Tests for app/api/routes/extraction.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

import app.api.routes.extraction as extraction_module
from app.models.graph import ExtractionResult, Node, Link
from app.services.task_queue import TaskQueue


def _make_extraction_result(success=True):
    result = ExtractionResult(
        nodes=[
            Node(id="python", type="skill", category="programming"),
            Node(id="software_engineer", type="role"),
        ],
        links=[Link(source="software_engineer", target="python", type="REQUIRES")],
        success=success,
        method="heuristic",
    )
    return result


@pytest.fixture(autouse=True)
def clear_tasks():
    TaskQueue._tasks.clear()
    yield
    TaskQueue._tasks.clear()


@pytest.fixture()
def fake_pipeline():
    pipeline = MagicMock()
    pipeline.extract_sync.return_value = {
        "extraction_result": _make_extraction_result(success=True),
        "method_used": "heuristic",
        "fallback_triggered": False,
    }
    pipeline.extract = AsyncMock(return_value={
        "extraction_result": _make_extraction_result(success=True),
    })
    return pipeline


@pytest.fixture()
def fake_gm():
    gm = MagicMock()
    gm.get_node.return_value = None
    gm.graph = MagicMock()
    gm.graph.has_edge.return_value = False
    gm.save_graph.return_value = None
    gm.add_node.return_value = None
    gm.add_edge.return_value = None
    return gm


@pytest.fixture()
def fake_queue():
    q = MagicMock()
    q.get_pending.return_value = []
    q.get_stats.return_value = {"total": 0, "pending": 0, "reviewed": 0}
    q.retry.return_value = None
    q.mark_reviewed.return_value = None
    q.remove.return_value = None
    return q


@pytest.fixture()
def client(fake_pipeline, fake_gm, fake_queue, monkeypatch):
    monkeypatch.setattr(extraction_module, "ExtractionPipeline", lambda **kwargs: fake_pipeline)
    monkeypatch.setattr(extraction_module, "GraphManager", lambda: fake_gm)
    monkeypatch.setattr(extraction_module, "PendingQueue", lambda: fake_queue)
    app = FastAPI()
    app.include_router(extraction_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /job
# ---------------------------------------------------------------------------

def test_extract_job_success(client, fake_pipeline, fake_gm):
    response = client.post("/job", json={
        "title": "Software Engineer",
        "description": "We need Python developers",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["graph_updated"] is True
    fake_gm.save_graph.assert_called()


def test_extract_job_extraction_fails(client, fake_pipeline):
    fake_pipeline.extract_sync.return_value = {
        "extraction_result": _make_extraction_result(success=False),
        "fallback_triggered": False,
    }
    response = client.post("/job", json={"title": "Role", "description": "desc"})
    assert response.status_code == 200
    body = response.json()
    assert body["graph_updated"] is False


def test_extract_job_with_company(client, fake_gm):
    response = client.post("/job", json={
        "title": "Dev",
        "description": "job",
        "company": "Acme",
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /job/background
# ---------------------------------------------------------------------------

def test_extract_job_background(client):
    response = client.post("/job/background", json={
        "title": "Engineer",
        "description": "We need Kubernetes skills",
    })
    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert "message" in body


# ---------------------------------------------------------------------------
# GET /job/{task_id}
# ---------------------------------------------------------------------------

def test_get_extraction_status_not_found(client):
    response = client.get("/job/nonexistent_task_99")
    assert response.status_code == 404


def test_get_extraction_status_found(client):
    from app.services.task_queue import TaskQueue, TaskStatus
    tid = TaskQueue.create_task("test")
    TaskQueue.update_task(tid, TaskStatus.COMPLETED, result={"done": True})
    response = client.get(f"/job/{tid}")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == tid


# ---------------------------------------------------------------------------
# POST /course
# ---------------------------------------------------------------------------

def test_extract_course_success(client, fake_pipeline, fake_gm):
    response = client.post("/course", json={
        "title": "Python Fundamentals",
        "description": "Learn Python programming",
        "provider": "Coursera",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["graph_updated"] is True


def test_extract_course_no_skills(client, fake_pipeline):
    fake_pipeline.extract_sync.return_value = {
        "extraction_result": _make_extraction_result(success=False),
    }
    response = client.post("/course", json={
        "title": "Generic Course",
        "description": "No skills here",
        "provider": "Udemy",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["graph_updated"] is False


# ---------------------------------------------------------------------------
# GET /pending
# ---------------------------------------------------------------------------

def test_get_pending_items(client, fake_queue):
    response = client.get("/pending")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "stats" in body


# ---------------------------------------------------------------------------
# POST /pending/{item_id}/retry
# ---------------------------------------------------------------------------

def test_retry_pending_item(client, fake_queue):
    response = client.post("/pending/item_001/retry")
    assert response.status_code == 200
    fake_queue.retry.assert_called_once_with("item_001")


# ---------------------------------------------------------------------------
# POST /pending/{item_id}/review
# ---------------------------------------------------------------------------

def test_mark_reviewed(client, fake_queue):
    response = client.post("/pending/item_002/review")
    assert response.status_code == 200
    fake_queue.mark_reviewed.assert_called_once_with("item_002")


# ---------------------------------------------------------------------------
# DELETE /pending/{item_id}
# ---------------------------------------------------------------------------

def test_delete_pending_item(client, fake_queue):
    response = client.delete("/pending/item_003")
    assert response.status_code == 200
    fake_queue.remove.assert_called_once_with("item_003")


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------

def test_list_tasks(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    body = response.json()
    assert "tasks" in body
