"""Tests for app/services/nlp_extractor.py."""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.nlp_extractor import NLPExtractor
from app.models.graph import ExtractionResult


@pytest.fixture(autouse=True)
def reset_nlp_state():
    """Reset class-level cached state between tests."""
    NLPExtractor._spacy_model = None
    NLPExtractor._skills_map = None
    yield
    NLPExtractor._spacy_model = None
    NLPExtractor._skills_map = None


@pytest.fixture()
def skills_library(tmp_path):
    data = {
        "skills": [
            {"id": "python", "name": "Python", "aliases": ["py", "python3"]},
            {"id": "docker", "name": "Docker", "aliases": ["containerization"]},
        ]
    }
    path = tmp_path / "skills_library.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def extractor(skills_library, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", skills_library)
    return NLPExtractor()


# ---------------------------------------------------------------------------
# _load_skills
# ---------------------------------------------------------------------------

def test_load_skills_from_file(extractor):
    skills_map = extractor._load_skills()
    assert "python" in skills_map
    assert "docker" in skills_map


def test_load_skills_missing_file(tmp_path, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SKILLS_LIBRARY_PATH", tmp_path / "missing.json")
    NLPExtractor._skills_map = None
    e = NLPExtractor()
    skills_map = e._load_skills()
    assert skills_map == {}


def test_load_skills_cached(extractor):
    """Second call should return cached value."""
    first = extractor._load_skills()
    second = extractor._load_skills()
    assert first is second


# ---------------------------------------------------------------------------
# _normalize_skill
# ---------------------------------------------------------------------------

def test_normalize_skill_lowercase(extractor):
    result = extractor._normalize_skill("Python")
    assert result == "python"


def test_normalize_skill_spaces_to_underscores(extractor):
    result = extractor._normalize_skill("machine learning")
    assert result == "machine_learning"


def test_normalize_skill_strips_special(extractor):
    result = extractor._normalize_skill("node.js!")
    assert "_" in result or "." not in result


# ---------------------------------------------------------------------------
# _matches_skill
# ---------------------------------------------------------------------------

def test_matches_skill_exact(extractor):
    assert extractor._matches_skill("python", "python", {}) is True


def test_matches_skill_partial(extractor):
    # "python" is a substring of "pythonic", so _matches_skill returns True
    assert extractor._matches_skill("pythonic", "python", {}) is True


def test_matches_skill_no_match(extractor):
    assert extractor._matches_skill("java", "python", {}) is False


# ---------------------------------------------------------------------------
# _init_spacy (spaCy not installed → graceful fallback)
# ---------------------------------------------------------------------------

def test_init_spacy_handles_model_not_found(extractor, monkeypatch):
    """Should not raise if spaCy model not found."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "spacy":
            raise OSError("No model")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    extractor._init_spacy()
    assert NLPExtractor._spacy_model is None


# ---------------------------------------------------------------------------
# _extract_entities (no spaCy → returns empty)
# ---------------------------------------------------------------------------

def test_extract_entities_no_spacy(extractor):
    NLPExtractor._spacy_model = None
    result = extractor._extract_entities("We need Python and Docker skills")
    assert result == set()


# ---------------------------------------------------------------------------
# _map_to_library
# ---------------------------------------------------------------------------

def test_map_to_library_exact_match(extractor):
    matched = extractor._map_to_library({"python"})
    assert "python" in matched


def test_map_to_library_alias_match(extractor):
    matched = extractor._map_to_library({"py"})
    assert "python" in matched


def test_map_to_library_no_match(extractor):
    matched = extractor._map_to_library({"ruby"})
    assert matched == {}


# ---------------------------------------------------------------------------
# extract (full pipeline)
# ---------------------------------------------------------------------------

def test_extract_no_spacy_returns_heuristic(extractor):
    result = extractor.extract("Backend Dev", "We need Python and Docker.")
    assert isinstance(result, ExtractionResult)


def test_extract_empty_text(extractor):
    result = extractor.extract("", "")
    assert isinstance(result, ExtractionResult)
