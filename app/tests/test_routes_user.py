"""Tests for app/api/routes/user.py."""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import MagicMock

import app.api.routes.user as user_module


@pytest.fixture()
def fake_gm():
    gm = MagicMock()
    gm.get_node.return_value = None
    gm.graph = MagicMock()
    gm.graph.has_edge.return_value = False
    gm.graph.__contains__ = MagicMock(return_value=False)
    gm.get_user_skills.return_value = ["python", "docker"]
    gm.save_graph.return_value = None
    gm.add_node.return_value = None
    gm.add_edge.return_value = None
    gm.remove_edge.return_value = None
    return gm


@pytest.fixture()
def client(fake_gm, monkeypatch):
    monkeypatch.setattr(user_module, "graph_manager", fake_gm)
    app = FastAPI()
    app.include_router(user_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST / – create user
# ---------------------------------------------------------------------------

def test_create_user_no_skills(client, fake_gm):
    response = client.post("/", json={"id": "u1", "name": "Alice", "skills": []})
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u1"
    fake_gm.add_node.assert_called_once()
    fake_gm.save_graph.assert_called_once()


def test_create_user_links_existing_skills(client, fake_gm):
    from app.models.graph import NodeType
    skill_node = MagicMock()
    skill_node.get.return_value = NodeType.SKILL.value
    fake_gm.get_node.return_value = skill_node

    response = client.post("/", json={"id": "u2", "name": "Bob", "skills": ["python"]})
    assert response.status_code == 200
    # add_edge should have been called for the skill
    fake_gm.add_edge.assert_called()


def test_create_user_skips_missing_skills(client, fake_gm):
    fake_gm.get_node.return_value = None  # skill doesn't exist in graph
    response = client.post("/", json={"id": "u3", "name": "Carol", "skills": ["unknownxyz"]})
    assert response.status_code == 200
    fake_gm.add_edge.assert_not_called()


# ---------------------------------------------------------------------------
# GET /{user_id}/skills
# ---------------------------------------------------------------------------

def test_get_user_skills(client, fake_gm):
    fake_gm.get_user_skills.return_value = ["python", "docker"]
    response = client.get("/u1/skills")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u1"
    assert "python" in body["skills"]


# ---------------------------------------------------------------------------
# PUT /{user_id}/skills
# ---------------------------------------------------------------------------

def test_update_user_skills(client, fake_gm):
    fake_gm.get_node.return_value = {"type": "skill"}
    fake_gm.graph.has_edge.return_value = False
    response = client.put("/u1/skills", json={"skills": ["python", "kubernetes"]})
    assert response.status_code == 200
    body = response.json()
    assert "python" in body["skills"]


def test_update_user_skips_already_linked_skills(client, fake_gm):
    fake_gm.get_node.return_value = {"type": "skill"}
    fake_gm.graph.has_edge.return_value = True  # edge already exists
    response = client.put("/u1/skills", json={"skills": ["python"]})
    assert response.status_code == 200
    fake_gm.add_edge.assert_not_called()


# ---------------------------------------------------------------------------
# DELETE /{user_id}
# ---------------------------------------------------------------------------

def test_delete_user_found(client, fake_gm):
    fake_gm.graph.__contains__ = MagicMock(return_value=True)
    fake_gm.graph.remove_node = MagicMock()
    response = client.delete("/u1")
    assert response.status_code == 200
    fake_gm.graph.remove_node.assert_called_once_with("u1")


def test_delete_user_not_found(client, fake_gm):
    fake_gm.graph.__contains__ = MagicMock(return_value=False)
    response = client.delete("/nonexistent")
    assert response.status_code == 404
