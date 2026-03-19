"""Tests for app/services/roadmap_generator.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.roadmap_generator import RoadmapGenerator, get_roadmap_generator
from app.models.user import Roadmap, WeekPlan


def _make_gap():
    gap = MagicMock()
    gap.user_skills = ["python"]
    gap.missing_skills = ["docker", "kubernetes"]
    gap.courses_for_gaps = {"docker": [{"title": "Docker Fundamentals", "url": "http://x.com"}], "kubernetes": []}
    return gap


@pytest.fixture(autouse=True)
def reset_singleton():
    import app.services.roadmap_generator as rg_mod
    rg_mod._roadmap_generator = None
    yield
    rg_mod._roadmap_generator = None


@pytest.fixture()
def generator():
    rg = RoadmapGenerator(api_key=None)
    rg.api_key = None  # override real settings.GROQ_API_KEY so no LLM is used
    rg.gap_analyzer = MagicMock()
    rg.gap_analyzer.analyze_gaps.return_value = _make_gap()
    rg.graph_manager = MagicMock()
    rg.graph_manager.get_node.return_value = {"category": "devops"}
    return rg


# ---------------------------------------------------------------------------
# _initialize_llm
# ---------------------------------------------------------------------------

def test_initialize_llm_no_key(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    rg = RoadmapGenerator(api_key=None)
    rg._initialize_llm()
    assert rg._llm is None


def test_initialize_llm_with_key(monkeypatch):
    monkeypatch.setattr("app.services.roadmap_generator.ChatGroq", MagicMock())
    rg = RoadmapGenerator(api_key="fake-key")
    rg._initialize_llm()
    assert rg._llm is not None


# ---------------------------------------------------------------------------
# _get_skill_milestones
# ---------------------------------------------------------------------------

def test_get_skill_milestones_cache_hit(generator):
    generator._milestones_cache["python"] = ["Step A", "Step B"]
    result = generator._get_skill_milestones("python")
    assert result == ["Step A", "Step B"]


def test_get_skill_milestones_default(generator):
    result = generator._get_skill_milestones("unknown_skill")
    assert "Learn fundamentals" in result


# ---------------------------------------------------------------------------
# generate_structured_roadmap
# ---------------------------------------------------------------------------

def test_generate_structured_roadmap_basic(generator):
    roadmap = generator.generate_structured_roadmap("user1", "devops_engineer")
    assert isinstance(roadmap, Roadmap)
    assert roadmap.user_id == "user1"
    assert roadmap.target_role == "devops_engineer"
    assert roadmap.total_weeks == 2  # 2 missing skills
    assert roadmap.ai_generated is False
    assert roadmap.fallback_used is True


def test_generate_structured_roadmap_node_not_found(generator):
    generator.graph_manager.get_node.return_value = None
    roadmap = generator.generate_structured_roadmap("user2", "backend_dev")
    assert isinstance(roadmap, Roadmap)
    assert roadmap.total_weeks == 2


def test_generate_structured_roadmap_empty_gaps(generator):
    gap = _make_gap()
    gap.missing_skills = []
    generator.gap_analyzer.analyze_gaps.return_value = gap
    roadmap = generator.generate_structured_roadmap("user3", "junior_dev")
    assert roadmap.total_weeks == 0
    assert roadmap.weeks == []


def test_generate_structured_roadmap_courses_truncated(generator):
    gap = _make_gap()
    gap.courses_for_gaps = {"docker": [{"title": f"Course {i}", "url": "http://x.com"} for i in range(5)]}
    gap.missing_skills = ["docker"]
    generator.gap_analyzer.analyze_gaps.return_value = gap
    roadmap = generator.generate_structured_roadmap("user4", "devops_engineer")
    # resources are truncated to 3
    assert len(roadmap.weeks[0].resources) == 3


# ---------------------------------------------------------------------------
# _generate_milestones_llm (async, no LLM)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_generate_milestones_llm_no_llm(generator):
    result = await generator._generate_milestones_llm(["python", "docker"])
    assert "python" in result
    assert isinstance(result["python"], list)


@pytest.mark.anyio
async def test_generate_milestones_llm_empty(generator):
    result = await generator._generate_milestones_llm([])
    assert result == {}


@pytest.mark.anyio
async def test_generate_milestones_llm_cache_hit(generator):
    generator._milestones_cache["docker,python"] = {"python": ["Step 1"], "docker": ["Step A"]}
    result = await generator._generate_milestones_llm(["python", "docker"])
    assert "python" in result


# ---------------------------------------------------------------------------
# generate_ai_roadmap (async, no LLM → fallback)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_generate_ai_roadmap_fallback_when_no_llm(generator):
    roadmap = await generator.generate_ai_roadmap("user1", "backend_dev")
    assert isinstance(roadmap, Roadmap)
    # No LLM → falls back to structured roadmap
    assert roadmap.ai_generated is False


@pytest.mark.anyio
async def test_generate_ai_roadmap_with_llm_response(generator, monkeypatch):
    fake_llm_data = {
        "weeks": [
            {"skill": "docker", "skill_category": "devops", "milestones": ["Step 1"]},
        ],
        "total_weeks": 1,
    }
    generator._generate_roadmap_llm = AsyncMock(return_value=fake_llm_data)
    generator._generate_milestones_llm = AsyncMock(return_value={"docker": ["Step 1"]})
    roadmap = await generator.generate_ai_roadmap("user1", "backend_dev")
    assert roadmap.ai_generated is True
    assert roadmap.total_weeks == 1


# ---------------------------------------------------------------------------
# Singleton getter
# ---------------------------------------------------------------------------

def test_get_roadmap_generator_singleton():
    g1 = get_roadmap_generator()
    g2 = get_roadmap_generator()
    assert g1 is g2
