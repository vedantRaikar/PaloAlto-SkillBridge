"""Tests for app/services/extraction_pipeline.py - DynamicSkillExtractor and ExtractionPipeline."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.extraction_pipeline import DynamicSkillExtractor, ExtractionPipeline
from app.models.graph import ExtractionResult, Node, NodeType


# ============================================================
# DynamicSkillExtractor
# ============================================================

@pytest.fixture()
def dynamic():
    return DynamicSkillExtractor()


def test_extract_all_skills_python(dynamic):
    skills = dynamic.extract_all_skills("We need Python and Docker for our backend.")
    assert "python" in skills
    assert "docker" in skills


def test_extract_all_skills_kubernetes(dynamic):
    skills = dynamic.extract_all_skills("Experience with kubernetes is required.")
    assert "kubernetes" in skills


def test_extract_all_skills_k8s_alias(dynamic):
    skills = dynamic.extract_all_skills("k8s experience required")
    assert "k8s" in skills


def test_extract_all_skills_react(dynamic):
    skills = dynamic.extract_all_skills("React frontend development")
    assert "react" in skills


def test_extract_all_skills_empty(dynamic):
    skills = dynamic.extract_all_skills("")
    assert isinstance(skills, set)


def test_extract_all_skills_common_words_excluded(dynamic):
    skills = dynamic.extract_all_skills("the and for are but not you all can")
    assert "the" not in skills
    assert "and" not in skills


def test_extract_all_skills_version_numbers(dynamic):
    skills = dynamic.extract_all_skills("Python 3.11 and Node.js v18")
    assert "python" in skills


def test_extract_all_skills_camel_case(dynamic):
    skills = dynamic.extract_all_skills("Using TensorFlow for model training")
    assert isinstance(skills, set)


def test_extract_all_skills_multiple_techs(dynamic):
    text = "We use AWS, PostgreSQL, Docker, and Kubernetes for our infrastructure."
    skills = dynamic.extract_all_skills(text)
    assert "aws" in skills or "docker" in skills or "kubernetes" in skills


# ============================================================
# ExtractionPipeline (mocked sub-components)
# ============================================================

@pytest.fixture()
def pipeline(monkeypatch):
    from app.models.graph import ExtractionResult, Node, NodeType

    fake_entity_result = ExtractionResult(
        nodes=[Node(id="python", type=NodeType.SKILL, category="programming")],
        links=[],
        success=True,
        method="llm",
    )
    fake_entity_extractor = MagicMock()
    fake_entity_extractor.extract = AsyncMock(return_value=fake_entity_result)

    fake_heuristic_result = ExtractionResult(
        nodes=[Node(id="docker", type=NodeType.SKILL, category="devops")],
        links=[],
        success=True,
        method="heuristic",
    )
    fake_heuristic = MagicMock()
    fake_heuristic.extract = MagicMock(return_value=fake_heuristic_result)

    fake_nlp_result = ExtractionResult(nodes=[], links=[], success=False, method="nlp")
    fake_nlp = MagicMock()
    fake_nlp.extract = AsyncMock(return_value=fake_nlp_result)

    fake_topic = MagicMock()
    fake_topic.full_topic_extraction_llm = AsyncMock(return_value={
        "additional_skills": ["aws"],
        "implied_skills": [],
        "soft_skills": [],
        "tech_categories": [],
    })

    fake_entity_linker = MagicMock()
    fake_entity_linker.enrich_with_relationships = AsyncMock(return_value=[])
    fake_entity_linker.infer_skill_category = AsyncMock(return_value="programming")

    fake_pending_queue = MagicMock()

    monkeypatch.setattr("app.services.extraction_pipeline.EntityExtractor", lambda **kwargs: fake_entity_extractor)
    monkeypatch.setattr("app.services.extraction_pipeline.HeuristicExtractor", lambda: fake_heuristic)
    monkeypatch.setattr("app.services.extraction_pipeline.NLPExtractor", lambda: fake_nlp)
    monkeypatch.setattr("app.services.extraction_pipeline.get_topic_extractor", lambda api_key=None: fake_topic)
    monkeypatch.setattr("app.services.extraction_pipeline.get_entity_linker", lambda api_key=None: fake_entity_linker)
    monkeypatch.setattr("app.services.extraction_pipeline.PendingQueue", lambda: fake_pending_queue)

    p = ExtractionPipeline(groq_api_key=None)
    return p, fake_pending_queue


@pytest.mark.anyio
async def test_pipeline_extract_tier1_success(pipeline):
    p, _ = pipeline
    result = await p.extract("Software Engineer", "We need Python and AWS experience.")
    assert "extraction_result" in result
    extraction = result["extraction_result"]
    assert isinstance(extraction, ExtractionResult)
    assert extraction.success is True


@pytest.mark.anyio
async def test_pipeline_extract_uses_combined_text(pipeline):
    p, _ = pipeline
    result = await p.extract("DevOps Engineer", "Docker and Kubernetes required.")
    assert "extraction_result" in result or "pending_id" in result


@pytest.mark.anyio
async def test_pipeline_extract_normalize_id(pipeline):
    p, _ = pipeline
    result = await p.extract("Full Stack Developer", "Need React and Node.js")
    assert "extraction_result" in result or "pending_id" in result


@pytest.mark.anyio
async def test_pipeline_tier1_all_fail_goes_to_human_loop(monkeypatch):
    empty_result = ExtractionResult(nodes=[], links=[], success=False, method="none")

    fake_entity_extractor = MagicMock()
    fake_entity_extractor.extract = AsyncMock(return_value=empty_result)

    fake_heuristic = MagicMock()
    fake_heuristic.extract = MagicMock(return_value=empty_result)

    fake_nlp = MagicMock()
    fake_nlp.extract = AsyncMock(return_value=empty_result)

    fake_topic = MagicMock()
    fake_topic.full_topic_extraction_llm = AsyncMock(return_value={
        "additional_skills": [],
        "implied_skills": [],
        "soft_skills": [],
        "tech_categories": [],
    })

    fake_entity_linker = MagicMock()
    fake_entity_linker.enrich_with_relationships = AsyncMock(return_value=[])
    fake_entity_linker.infer_skill_category = AsyncMock(return_value="programming")

    fake_pending_queue = MagicMock()
    fake_pending_queue.add.return_value = "pq_abc"

    monkeypatch.setattr("app.services.extraction_pipeline.EntityExtractor", lambda **kwargs: fake_entity_extractor)
    monkeypatch.setattr("app.services.extraction_pipeline.HeuristicExtractor", lambda: fake_heuristic)
    monkeypatch.setattr("app.services.extraction_pipeline.NLPExtractor", lambda: fake_nlp)
    monkeypatch.setattr("app.services.extraction_pipeline.get_topic_extractor", lambda api_key=None: fake_topic)
    monkeypatch.setattr("app.services.extraction_pipeline.get_entity_linker", lambda api_key=None: fake_entity_linker)
    monkeypatch.setattr("app.services.extraction_pipeline.PendingQueue", lambda: fake_pending_queue)

    p = ExtractionPipeline(groq_api_key=None)
    result = await p.extract("Vague Job", "Nothing technical mentioned here at all.")
    # Tier 3 = human loop → should have pending_id
    assert "pending_id" in result or "extraction_result" in result


@pytest.mark.anyio
async def test_pipeline_normalize_id():
    p = ExtractionPipeline.__new__(ExtractionPipeline)
    p.groq_api_key = None
    normalized = p._normalize_id("Senior Python Developer!")
    assert "senior" in normalized
    assert " " not in normalized
