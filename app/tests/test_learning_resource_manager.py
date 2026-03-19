import networkx as nx
import pytest

import app.services.learning_resource_manager as lrm_module
from app.models.certification import Certification, CertificationSearchResponse
from app.models.course import Course, CourseSearchRequest, CourseSearchResponse


class FakeGraphManager:
    def __init__(self):
        self.graph = nx.DiGraph()

    def get_node(self, node_id):
        if node_id in self.graph.nodes:
            return {"id": node_id, **self.graph.nodes[node_id]}
        return None

    def add_node(self, node):
        data = node.model_dump()
        node_id = data.pop("id")
        self.graph.add_node(node_id, **data)

    def add_edge(self, source, target, link_type, weight=1.0):
        edge_type = link_type.value if hasattr(link_type, "value") else link_type
        self.graph.add_edge(source, target, type=edge_type, weight=weight)

    def save_graph(self):
        return None


class FakeCourseAggregator:
    def __init__(self, courses):
        self._courses = courses

    async def search_all(self, skill, providers=None, max_results=10, free_only=False, min_rating=None):
        return CourseSearchResponse(
            courses=self._courses[:max_results],
            total=min(len(self._courses), max_results),
            provider_breakdown={self._courses[0].provider: min(len(self._courses), max_results)} if self._courses else {},
            search_skill=skill,
        )

    def search(self, skill, max_results=5):
        return CourseSearchResponse(
            courses=self._courses[:max_results],
            total=min(len(self._courses), max_results),
            provider_breakdown={self._courses[0].provider: min(len(self._courses), max_results)} if self._courses else {},
            search_skill=skill,
        )


class FakeCertService:
    def __init__(self, certifications):
        self._certifications = certifications

    def search(self, skill=None, provider=None, level=None):
        return CertificationSearchResponse(
            certifications=self._certifications,
            total=len(self._certifications),
            providers_found=[c.provider for c in self._certifications],
            search_params={"skill": skill, "provider": provider, "level": level},
        )

    def get_by_skill(self, skill_id):
        return self._certifications

    def recommend_for_skills(self, skills):
        return self._certifications

    def get_career_path(self, cert_id):
        return self._certifications

    def get_prerequisites(self, cert_id):
        return []


def _sample_course():
    return Course(
        id="freecodecamp_python_course",
        title="Python Course",
        provider="freecodecamp",
        url="https://example.com/python",
        instructor="Instructor",
        duration_hours=10,
        rating=4.8,
        num_students=1200,
        is_free=True,
        level="beginner",
        skills_taught=["python"],
        description="Python basics",
    )


def _sample_cert():
    return Certification(
        id="aws_saa",
        name="AWS Certified Solutions Architect - Associate",
        provider="aws",
        certification_url="https://example.com/cert",
        level="associate",
        skills_covered=["aws", "cloud"],
    )


@pytest.fixture
def manager(monkeypatch):
    course = _sample_course()
    cert = _sample_cert()

    monkeypatch.setattr(lrm_module, "GraphManager", FakeGraphManager)
    monkeypatch.setattr(lrm_module, "get_course_aggregator", lambda: FakeCourseAggregator([course]))
    monkeypatch.setattr(lrm_module, "get_certification_service", lambda: FakeCertService([cert]))
    monkeypatch.setattr(
        lrm_module.LearningResourceManager,
        "_load_json",
        lambda self, path: {} if path.endswith("resource_map.json") else [],
    )

    mgr = lrm_module.LearningResourceManager()
    mgr._save_json = lambda path, data: None
    return mgr


@pytest.mark.anyio
async def test_search_courses_adds_course_nodes(manager):
    request = CourseSearchRequest(skill="python", max_results=5)

    response = await manager.search_courses(request)

    assert response.total == 1
    assert "freecodecamp_python_course" in manager.gm.graph.nodes
    assert "python" in manager.gm.graph.nodes


def test_recommend_certifications_for_skills_returns_enriched_payload(manager):
    recommendations = manager.recommend_certifications_for_skills(["aws"])

    assert len(recommendations) == 1
    assert "certification" in recommendations[0]
    assert "career_path" in recommendations[0]
    assert recommendations[0]["skill_match_count"] == 0


def test_get_learning_resources_for_skill_combines_courses_and_certs(manager):
    manager._search_courses_for_skill = lambda skill_id: [_sample_course()]

    resources = manager.get_learning_resources_for_skill("python")

    assert resources["skill_id"] == "python"
    assert len(resources["courses"]) == 1
    assert len(resources["certifications"]) == 1
    assert resources["total_resources"] == 2


def test_generate_learning_paths_includes_cert_and_multi_skill_paths(manager):
    paths = manager._generate_learning_paths(["aws", "python"])

    assert len(paths) >= 2
    assert any("Learning Path" in p["name"] for p in paths)
    assert any(p["name"] == "Multi-Skill Learning Path" for p in paths)


def test_get_courses_for_skill_reads_graph_predecessors(manager):
    manager.gm.graph.add_node(
        "course_demo",
        type="course",
        title="Demo Course",
        provider="demo",
        url="https://example.com/demo",
        is_free=True,
        level="beginner",
    )
    manager.gm.graph.add_node("python", type="skill", title="Python")
    manager.gm.graph.add_edge("course_demo", "python", type="teaches")

    courses = manager._get_courses_for_skill("python")

    assert len(courses) == 1
    assert courses[0].id == "course_demo"


def test_get_graph_stats_reports_course_and_cert_counts(manager):
    manager.gm.graph.add_node("course_1", type="course", category="freecodecamp")
    manager.gm.graph.add_node("cert_1", type="certification", category="aws")

    stats = manager.get_graph_stats()

    assert stats["course_count"] >= 1
    assert stats["certification_count"] >= 1
