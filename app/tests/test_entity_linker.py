"""Tests for app/services/entity_linker.py."""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.entity_linker import EntityLinker, get_entity_linker
from app.models.graph import Node, NodeType, Link, LinkType


@pytest.fixture(autouse=True)
def reset_singleton():
    import app.services.entity_linker as el_mod
    el_mod._entity_linker = None
    yield
    el_mod._entity_linker = None


@pytest.fixture()
def skills_lib(tmp_path):
    data = {
        "skills": [
            {"id": "python", "name": "Python", "category": "programming", "aliases": []},
            {"id": "docker", "name": "Docker", "category": "devops", "aliases": []},
        ]
    }
    path = tmp_path / "skills_library.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def linker(skills_lib, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", skills_lib)
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    el = EntityLinker(api_key=None)
    el.gm = MagicMock()
    el.gm.get_node.return_value = None
    el.gm.add_node = MagicMock()
    el.gm.add_edge = MagicMock()
    el.gm.graph = MagicMock()
    el.gm.graph.has_edge.return_value = False
    return el


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def test_initialize_llm_no_key(linker):
    linker._initialize_llm()
    assert linker._llm is None


def test_initialize_llm_with_key(monkeypatch, linker):
    monkeypatch.setattr("app.services.entity_linker.ChatGroq", MagicMock())
    linker.api_key = "fake-key"
    linker._initialize_llm()
    assert linker._llm is not None


# ---------------------------------------------------------------------------
# _load_skills
# ---------------------------------------------------------------------------

def test_load_skills_from_file(linker):
    assert "python" in linker.skills_map
    assert "docker" in linker.skills_map


# ---------------------------------------------------------------------------
# infer_skill_category_sync
# ---------------------------------------------------------------------------

def test_infer_category_sync_from_cache(linker):
    linker._category_cache["react"] = "frontend"
    result = linker.infer_skill_category_sync("react")
    assert result == "frontend"


def test_infer_category_sync_from_skills_map(linker):
    result = linker.infer_skill_category_sync("python")
    assert result == "programming"


def test_infer_category_sync_unknown(linker):
    result = linker.infer_skill_category_sync("totally_unknown_skill")
    assert result == "unknown"


# ---------------------------------------------------------------------------
# infer_skill_relationships_sync
# ---------------------------------------------------------------------------

def test_infer_relationships_sync_empty(linker):
    result = linker.infer_skill_relationships_sync("python")
    assert isinstance(result, list)
    assert result == []


def test_infer_relationships_sync_cached(linker):
    linker._relationships_cache["python"] = {"related_skills": ["django", "flask"]}
    result = linker.infer_skill_relationships_sync("python")
    assert "django" in result


# ---------------------------------------------------------------------------
# link_entity_to_graph_sync
# ---------------------------------------------------------------------------

def test_link_entity_sync_no_category_node(linker):
    node = Node(id="python", type=NodeType.SKILL, category="programming")
    linker.gm.get_node.return_value = None
    links = linker.link_entity_to_graph_sync(node)
    # No category node in graph → no links
    assert links == []


def test_link_entity_sync_with_category_node(linker):
    linker.gm.get_node.side_effect = lambda nid: (
        {"type": "category"} if nid == "category_programming" else None
    )
    node = Node(id="python", type=NodeType.SKILL, category="programming")
    links = linker.link_entity_to_graph_sync(node)
    assert len(links) > 0
    assert any(link[2] == LinkType.PART_OF for link in links)


# ---------------------------------------------------------------------------
# link_role_to_graph
# ---------------------------------------------------------------------------

def test_link_role_to_graph(linker):
    linker.gm.get_node.side_effect = lambda nid: (
        {"type": "skill"} if nid in ["python", "docker"] else None
    )
    links = linker.link_role_to_graph("backend_dev", ["python", "docker", "unknown_skill"])
    # 2 existing skills → 2 links
    skill_links = [l for l in links if l[2] == LinkType.REQUIRES]
    assert len(skill_links) == 2


def test_link_role_to_graph_empty_skills(linker):
    links = linker.link_role_to_graph("role1", [])
    assert links == []


# ---------------------------------------------------------------------------
# link_course_to_graph
# ---------------------------------------------------------------------------

def test_link_course_to_graph(linker):
    linker.gm.get_node.side_effect = lambda nid: (
        {"type": "skill"} if nid == "python" else None
    )
    links = linker.link_course_to_graph("python_course", ["python", "java"])
    teaches_links = [l for l in links if l[2] == LinkType.TEACHES]
    assert len(teaches_links) == 1


# ---------------------------------------------------------------------------
# link_user_to_graph
# ---------------------------------------------------------------------------

def test_link_user_to_graph(linker):
    linker.gm.get_node.side_effect = lambda nid: (
        {"type": "skill"} if nid in ["python"] else None
    )
    links = linker.link_user_to_graph("user1", ["python", "nonexistent"])
    assert any(l[2] == LinkType.HAS_SKILL for l in links)


# ---------------------------------------------------------------------------
# resolve_skill_to_canonical
# ---------------------------------------------------------------------------

def test_resolve_skill_to_canonical(linker):
    linker.deduplicator = MagicMock()
    linker.deduplicator.suggest_canonical_form.return_value = "python"
    result = linker.resolve_skill_to_canonical("py")
    assert result == "python"


def test_resolve_skill_to_canonical_no_suggestion(linker):
    linker.deduplicator = MagicMock()
    linker.deduplicator.suggest_canonical_form.return_value = None
    linker.deduplicator.normalize_entity.return_value = "python"
    result = linker.resolve_skill_to_canonical("python")
    assert result == "python"


# ---------------------------------------------------------------------------
# _infer_category_llm (async, no LLM)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_infer_category_llm_no_llm_unknown(linker):
    result = await linker._infer_category_llm("totally_new_skill")
    assert result == "unknown"


@pytest.mark.anyio
async def test_infer_category_llm_from_skills_map(linker):
    result = await linker._infer_category_llm("python")
    assert result == "programming"


@pytest.mark.anyio
async def test_infer_category_llm_cached(linker):
    linker._category_cache["react"] = "frontend"
    result = await linker._infer_category_llm("react")
    assert result == "frontend"


# ---------------------------------------------------------------------------
# infer_skill_category (async)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_infer_skill_category_async(linker):
    result = await linker.infer_skill_category("python")
    assert result == "programming"


# ---------------------------------------------------------------------------
# infer_skill_relationships (async, no LLM)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_infer_skill_relationships_async_no_llm(linker):
    result = await linker.infer_skill_relationships("python")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# link_entity_to_graph (async)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_link_entity_to_graph_async_no_category_node(linker):
    linker.gm.get_node.return_value = None
    node = Node(id="react", type=NodeType.SKILL, category="frontend")
    links = await linker.link_entity_to_graph(node)
    assert isinstance(links, list)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def test_get_entity_linker_singleton(skills_lib, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", skills_lib)
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    el1 = get_entity_linker()
    el2 = get_entity_linker()
    assert el1 is el2
