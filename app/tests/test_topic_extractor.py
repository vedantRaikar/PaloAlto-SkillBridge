"""Tests for app/services/topic_extractor.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.topic_extractor import TopicExtractor, get_topic_extractor


@pytest.fixture(autouse=True)
def reset_singleton():
    import app.services.topic_extractor as te_mod
    te_mod._topic_extractor = None
    yield
    te_mod._topic_extractor = None


@pytest.fixture()
def extractor(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    return TopicExtractor(api_key=None)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def test_initialize_no_api_key(extractor):
    extractor._initialize_llm()
    assert extractor._llm is None


def test_initialize_with_api_key(monkeypatch):
    monkeypatch.setattr("app.services.topic_extractor.ChatGroq", MagicMock())
    te = TopicExtractor(api_key="fake-key")
    te._initialize_llm()
    assert te._llm is not None


# ---------------------------------------------------------------------------
# _load_skills
# ---------------------------------------------------------------------------

def test_load_skills_no_file(extractor):
    assert isinstance(extractor.skills_map, dict)


# ---------------------------------------------------------------------------
# _extract_words
# ---------------------------------------------------------------------------

def test_extract_words_basic(extractor):
    words = extractor._extract_words("We need Python and Docker skills")
    assert "python" in words
    assert "docker" in words


def test_extract_words_empty(extractor):
    words = extractor._extract_words("")
    assert words == []


# ---------------------------------------------------------------------------
# _normalize_skill_name
# ---------------------------------------------------------------------------

def test_normalize_skill_name_spaces(extractor):
    result = extractor._normalize_skill_name("machine learning")
    assert result == "machine_learning"


def test_normalize_skill_name_uppercase(extractor):
    result = extractor._normalize_skill_name("Python")
    assert result == "python"


def test_normalize_skill_name_special_chars(extractor):
    result = extractor._normalize_skill_name("node.js!")
    assert "." not in result
    assert "!" not in result


def test_normalize_skill_name_hyphens(extractor):
    result = extractor._normalize_skill_name("ci-cd")
    assert result == "ci_cd"


# ---------------------------------------------------------------------------
# Sync stubs (always return empty/None)
# ---------------------------------------------------------------------------

def test_extract_topics_returns_empty(extractor):
    assert extractor.extract_topics("some text") == []


def test_extract_implied_skills_returns_empty(extractor):
    assert extractor.extract_implied_skills(["python"]) == []


def test_extract_soft_skills_returns_empty(extractor):
    assert extractor.extract_soft_skills("some text") == []


def test_extract_certifications_returns_empty(extractor):
    assert extractor.extract_certifications("text with AWS cert") == []


def test_extract_experience_level_returns_none(extractor):
    assert extractor.extract_experience_level("5 years required") is None


def test_extract_tools_returns_empty(extractor):
    assert extractor.extract_tools("We use Docker") == []


def test_full_topic_extraction_sync(extractor):
    result = extractor.full_topic_extraction("some text", ["python"])
    assert "additional_skills" in result
    assert "python" in result["additional_skills"]


# ---------------------------------------------------------------------------
# Async methods (no LLM → return defaults)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_extract_skills_llm_no_llm(extractor):
    result = await extractor.extract_skills_llm("Dev", "Need Python and Docker")
    assert result == []


@pytest.mark.anyio
async def test_extract_topics_llm_no_llm(extractor):
    result = await extractor.extract_topics_llm("Dev", "Python developer needed")
    assert result["tech_categories"] == []
    assert result["experience_level"] == "unknown"


@pytest.mark.anyio
async def test_extract_soft_skills_llm_no_llm(extractor):
    result = await extractor.extract_soft_skills_llm("Need good communication")
    assert result == []


@pytest.mark.anyio
async def test_extract_certifications_llm_no_llm(extractor):
    result = await extractor.extract_certifications_llm("AWS certification preferred")
    assert result == []


@pytest.mark.anyio
async def test_extract_experience_level_llm_no_llm(extractor):
    result = await extractor.extract_experience_level_llm("Senior Dev", "5+ years required")
    assert result["experience_level"] == "unknown"


@pytest.mark.anyio
async def test_full_topic_extraction_llm_no_llm(extractor):
    result = await extractor.full_topic_extraction_llm("Python Dev", "We need Python skills", ["python"])
    assert "additional_skills" in result
    assert isinstance(result["implied_skills"], list)


# ---------------------------------------------------------------------------
# Cache in extract_skills_llm
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_extract_skills_llm_cache(extractor):
    cache_key = f"skills_{hash('Dev' + 'Need Python'[:100])}"
    extractor._cache[cache_key] = [{"id": "python", "name": "Python"}]
    result = await extractor.extract_skills_llm("Dev", "Need Python")
    assert result[0]["id"] == "python"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def test_get_topic_extractor_returns_same(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    e1 = get_topic_extractor()
    e2 = get_topic_extractor()
    assert e1 is e2
