"""Tests for app/services/heuristic_extractor.py."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.heuristic_extractor import HeuristicExtractor
from app.models.graph import ExtractionResult


@pytest.fixture()
def extractor():
    return HeuristicExtractor()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def test_extractor_loads_skills_map(extractor):
    # skills_map should be a dict (possibly empty if file missing)
    assert isinstance(extractor.skills_map, dict)


# ---------------------------------------------------------------------------
# _create_pattern
# ---------------------------------------------------------------------------

def test_create_pattern_with_aliases(extractor):
    pattern = extractor._create_pattern("python", ["py", "python3"])
    assert "python" in pattern
    assert "py" in pattern
    assert "python3" in pattern


def test_create_pattern_no_aliases(extractor):
    pattern = extractor._create_pattern("react", [])
    assert "react" in pattern


# ---------------------------------------------------------------------------
# extract_skills from text
# ---------------------------------------------------------------------------

def test_extract_skills_finds_explicit_skill(extractor):
    # Inject a minimal skills_map to avoid dependency on disk data
    extractor.skills_map = {
        "python": {"id": "python", "aliases": ["py"]},
        "docker": {"id": "docker", "aliases": []},
    }
    found = extractor.extract_skills("This role requires Python and Docker experience.")
    assert "python" in found


def test_extract_skills_finds_alias(extractor):
    extractor.skills_map = {
        "python": {"id": "python", "aliases": ["py"]},
    }
    found = extractor.extract_skills("Experience with py programming.")
    assert "python" in found


def test_extract_skills_empty_text(extractor):
    extractor.skills_map = {"python": {"id": "python", "aliases": []}}
    found = extractor.extract_skills("")
    assert found == set()


def test_extract_skills_no_match(extractor):
    extractor.skills_map = {"python": {"id": "python", "aliases": []}}
    found = extractor.extract_skills("We need a great communicator.")
    assert "python" not in found


# ---------------------------------------------------------------------------
# extract (full pipeline)
# ---------------------------------------------------------------------------

def test_extract_returns_extraction_result(extractor):
    extractor.skills_map = {
        "python": {"id": "python", "category": "programming", "aliases": []},
    }
    result = extractor.extract("Python Developer", "We need a Python expert.")
    assert isinstance(result, ExtractionResult)
    assert result.method == "heuristic"


def test_extract_success_when_skills_found(extractor):
    extractor.skills_map = {
        "python": {"id": "python", "category": "programming", "aliases": []},
    }
    result = extractor.extract("Python Dev", "Strong Python skills required.")
    assert result.success is True
    skill_ids = [n.id for n in result.nodes]
    assert "python" in skill_ids


def test_extract_failure_when_no_skills(extractor):
    extractor.skills_map = {"python": {"id": "python", "aliases": []}}
    result = extractor.extract("Manager", "Great communicator needed.")
    assert result.success is False


def test_extract_creates_links(extractor):
    extractor.skills_map = {
        "python": {"id": "python", "category": "programming", "aliases": []},
    }
    result = extractor.extract("Python Dev", "Python required.")
    if result.success:
        assert len(result.links) > 0
        assert result.links[0].target == "python"


def test_extract_empty_skills_map(extractor):
    extractor.skills_map = {}
    result = extractor.extract("Some Title", "Some description")
    assert result.success is False
    assert result.nodes == []
    assert result.links == []
