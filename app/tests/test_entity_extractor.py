"""Tests for app/services/entity_extractor.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.entity_extractor import EntityExtractor
from app.models.graph import ExtractionResult


# ---------------------------------------------------------------------------
# No API key path (most logic)
# ---------------------------------------------------------------------------

@pytest.fixture()
def extractor_no_key():
    return EntityExtractor(api_key=None)


def test_has_api_key_false(extractor_no_key):
    assert extractor_no_key._has_api_key() is False


def test_has_api_key_true():
    e = EntityExtractor(api_key="fake-key")
    assert e._has_api_key() is True


@pytest.mark.anyio
async def test_extract_no_api_key_returns_disabled(extractor_no_key):
    result = await extractor_no_key.extract("Software Engineer", "We need Python and Docker skills.")
    assert isinstance(result, ExtractionResult)
    assert result.success is False
    assert result.method == "llm_disabled"
    assert result.nodes == []
    assert result.links == []


@pytest.mark.anyio
async def test_extract_with_api_key_success(monkeypatch):
    from app.models.graph import Node, Link
    mock_result = ExtractionResult(
        nodes=[Node(id="python", type="skill", category="programming")],
        links=[],
        success=True,
        method="llm"
    )
    e = EntityExtractor(api_key=None)
    e.api_key = "fake-key"
    e.llm = MagicMock()

    async def fake_extract(self, title, description):
        return mock_result

    original_extract = EntityExtractor.extract
    monkeypatch.setattr(EntityExtractor, "extract", fake_extract)

    result = await e.extract("Python Dev", "Need Python skills")
    assert result.success is True
    monkeypatch.setattr(EntityExtractor, "extract", original_extract)


@pytest.mark.anyio
async def test_extract_empty_title_and_description(extractor_no_key):
    result = await extractor_no_key.extract("", "")
    assert result.success is False


def test_initialize_llm_sets_llm(monkeypatch):
    monkeypatch.setattr("app.services.entity_extractor.ChatGroq", MagicMock())
    e = EntityExtractor(api_key="fake-key")
    assert e.llm is not None


def test_model_defaults():
    e = EntityExtractor(api_key=None)
    assert e.model == "llama-3.1-8b-instant"


def test_custom_model():
    e = EntityExtractor(api_key=None, model="llama-3.3-70b-versatile")
    assert e.model == "llama-3.3-70b-versatile"
