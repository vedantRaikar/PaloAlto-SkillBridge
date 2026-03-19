"""Tests for app/services/resolver.py."""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.resolver import SkillResolver, SkillNormalizationResult, SkillResolutionResult


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset SkillResolver singleton state between tests."""
    SkillResolver._instance = None
    SkillResolver._llm = None
    SkillResolver._skills_cache = None
    SkillResolver._category_cache = {}
    yield
    SkillResolver._instance = None
    SkillResolver._llm = None
    SkillResolver._skills_cache = None
    SkillResolver._category_cache = {}


@pytest.fixture()
def skills_library(tmp_path):
    data = {
        "skills": [
            {"id": "python", "name": "Python"},
            {"id": "docker", "name": "Docker"},
            {"id": "kubernetes", "name": "Kubernetes"},
        ]
    }
    path = tmp_path / "skills_library.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def resolver(skills_library, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", skills_library)
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    return SkillResolver()


# ---------------------------------------------------------------------------
# Singleton behavior
# ---------------------------------------------------------------------------

def test_singleton(resolver):
    r2 = SkillResolver()
    assert resolver is r2


# ---------------------------------------------------------------------------
# _load_skills_cache
# ---------------------------------------------------------------------------

def test_skills_cache_loaded(resolver):
    assert "python" in SkillResolver._skills_cache
    assert "docker" in SkillResolver._skills_cache


def test_skills_cache_missing_file(tmp_path, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    SkillResolver._instance = None
    SkillResolver._skills_cache = None
    r = SkillResolver()
    assert SkillResolver._skills_cache == []


# ---------------------------------------------------------------------------
# _normalize_skill_llm (no LLM → fallback)
# ---------------------------------------------------------------------------

def test_normalize_skill_llm_no_llm(resolver):
    result = resolver._normalize_skill_llm("React.js")
    assert isinstance(result, SkillNormalizationResult)
    assert result.canonical_name == "react.js"
    assert result.alternatives == []


# ---------------------------------------------------------------------------
# _resolve_skills_llm (no LLM → identity mapping)
# ---------------------------------------------------------------------------

def test_resolve_skills_llm_no_llm(resolver):
    result = resolver._resolve_skills_llm(["React.js", "PostgreSQL"])
    assert isinstance(result, SkillResolutionResult)
    assert "React.js" in result.resolved_skills
    assert result.unknown_skills == []


# ---------------------------------------------------------------------------
# resolve_skill (no LLM)
# ---------------------------------------------------------------------------

def test_resolve_skill_no_llm_lowercase(resolver):
    result = resolver.resolve_skill("Python")
    assert result == "python"


def test_resolve_skill_spaces_to_underscores(resolver):
    result = resolver.resolve_skill("machine learning")
    assert result == "machine_learning"


# ---------------------------------------------------------------------------
# resolve_all_skills_llm (no LLM)
# ---------------------------------------------------------------------------

def test_resolve_all_skills_llm_no_llm(resolver):
    result = resolver.resolve_all_skills_llm(["React", "Docker"])
    assert isinstance(result, dict)
    assert "React" in result


# ---------------------------------------------------------------------------
# resolve_skill_llm
# ---------------------------------------------------------------------------

def test_resolve_skill_llm_no_llm(resolver):
    result = resolver.resolve_skill_llm("k8s")
    assert isinstance(result, str)
    assert result == "k8s"


# ---------------------------------------------------------------------------
# _analyze_skills_llm (no LLM → empty)
# ---------------------------------------------------------------------------

def test_analyze_skills_llm_no_llm(resolver):
    from app.services.resolver import SkillAnalysisResult
    result = resolver._analyze_skills_llm("I know Python and Docker")
    assert isinstance(result, SkillAnalysisResult)
    assert result.extracted_skills == []


# ---------------------------------------------------------------------------
# resolve_from_text (if it exists)
# ---------------------------------------------------------------------------

def test_resolve_from_text_no_llm(resolver):
    # This wraps _analyze_skills_llm
    if hasattr(resolver, "resolve_from_text"):
        result = resolver.resolve_from_text("Experienced in Python and React")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# LLM path tests (with mock LLM)
# ---------------------------------------------------------------------------

def test_normalize_skill_llm_with_llm(resolver, monkeypatch):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "canonical_name": "react",
        "category": "frontend",
        "alternatives": ["reactjs"],
        "is_primary": True,
        "related_skills": ["typescript"],
    }
    SkillResolver._llm = MagicMock()
    monkeypatch.setattr(
        "app.services.resolver.SKILL_NORMALIZATION_PROMPT",
        MagicMock(__or__=lambda s, o: MagicMock(__or__=lambda s2, o2: mock_chain))
    )
    result = resolver._normalize_skill_llm("React")
    assert result.canonical_name == "react"


def test_resolve_skills_llm_with_llm_exception(resolver):
    SkillResolver._llm = MagicMock()
    SkillResolver._llm.__or__ = MagicMock(side_effect=Exception("LLM error"))
    # Should fall back gracefully
    result = resolver._resolve_skills_llm(["python"])
    assert isinstance(result, SkillResolutionResult)
