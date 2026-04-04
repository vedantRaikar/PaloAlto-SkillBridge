from unittest.mock import MagicMock
import networkx as nx

from app.models.graph import Node, NodeType
from app.services.graph_manager import GraphManager


def test_add_user_skill_creates_skill_node_and_links_resources(monkeypatch):
    gm = GraphManager()
    GraphManager._graph = nx.DiGraph()
    gm._initialize_empty_graph()
    gm.save_graph = MagicMock()

    gm.add_node(Node(id="user_demo", type=NodeType.USER, title="Demo User"))

    fake_mapper = MagicMock()
    fake_mapper.get_learning_path.return_value = [
        {
            "title": "Python for Everybody",
            "provider": "edx",
            "url": "https://www.edx.org/search?q=python",
            "instructor": "Coursera",
            "rating": 4.8,
            "level": "all",
            "source": "edx_catalog",
        }
    ]

    fake_cert = MagicMock()
    fake_cert.get_by_skill.return_value = []

    monkeypatch.setattr(
        "app.services.knowledge_sources.onet_integration.get_skill_mapper",
        lambda: fake_mapper,
    )
    monkeypatch.setattr(
        "app.services.cert_discovery.service.get_certification_service",
        lambda: fake_cert,
    )

    skill_id = gm.add_user_skill("user_demo", "Python", enrich_resources=True)

    assert skill_id == "python"
    assert gm.node_exists("python")
    assert gm.graph.has_edge("user_demo", "python")
    course_ids = [target for _, target in gm.graph.out_edges("python") if gm.graph.nodes[target].get("type") == "course"]
    assert len(course_ids) == 1
    course_node = gm.graph.nodes[course_ids[0]]
    assert course_node["metadata"]["source"] == "edx_catalog"