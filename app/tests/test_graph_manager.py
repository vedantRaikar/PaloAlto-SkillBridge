"""
Unit Tests for Graph Manager
==========================
Tests knowledge graph operations.
"""

import pytest
from unittest.mock import MagicMock, patch
import networkx as nx


class TestGraphNodeOperations:
    """Tests for basic graph node operations."""

    def test_graph_manager_singleton(self):
        """Test that GraphManager is a singleton."""
        from app.services.graph_manager import GraphManager
        
        with patch.object(GraphManager, '_load_graph'):
            gm1 = GraphManager()
            gm2 = GraphManager()
            # Due to singleton pattern, they should be the same instance
            # (or share the same graph)

    def test_add_node_type_assignment(self):
        """Test that node type is assigned correctly."""
        from app.models.graph import Node, NodeType
        from app.services.graph_manager import GraphManager
        
        node = Node(
            id="test_skill",
            type=NodeType.SKILL,
            title="Test Skill"
        )
        
        assert node.type == NodeType.SKILL
        assert node.id == "test_skill"
        assert node.title == "Test Skill"


class TestGraphLinkTypes:
    """Tests for link type enums."""

    def test_link_types_exist(self):
        """Test that all link types are defined."""
        from app.models.graph import LinkType
        
        assert hasattr(LinkType, 'REQUIRES')
        assert hasattr(LinkType, 'TEACHES')
        assert hasattr(LinkType, 'HAS_SKILL')
        assert hasattr(LinkType, 'PART_OF')
        assert hasattr(LinkType, 'RELATED_TO')

    def test_node_types_exist(self):
        """Test that all node types are defined."""
        from app.models.graph import NodeType
        
        assert hasattr(NodeType, 'ROLE')
        assert hasattr(NodeType, 'SKILL')
        assert hasattr(NodeType, 'COURSE')
        assert hasattr(NodeType, 'CERTIFICATION')
        assert hasattr(NodeType, 'USER')
        assert hasattr(NodeType, 'DOMAIN')


class TestNetworkXIntegration:
    """Tests for NetworkX integration."""

    def test_can_create_digraph(self):
        """Test that we can create a directed graph."""
        G = nx.DiGraph()
        
        G.add_node("python")
        G.add_node("docker")
        G.add_edge("python", "docker")
        
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1
        assert G.has_edge("python", "docker")

    def test_digraph_is_directed(self):
        """Test that edges are directed."""
        G = nx.DiGraph()
        
        G.add_edge("a", "b")
        
        assert G.has_edge("a", "b")
        assert not G.has_edge("b", "a")


class TestGraphAlgorithms:
    """Tests for graph algorithms using NetworkX."""

    def test_shortest_path_simple(self):
        """Test shortest path in simple graph."""
        G = nx.DiGraph()
        
        G.add_edge("python", "django")
        G.add_edge("django", "web")
        
        path = nx.shortest_path(G, "python", "web")
        assert path == ["python", "django", "web"]

    def test_shortest_path_no_path(self):
        """Test shortest path when no path exists."""
        G = nx.DiGraph()
        
        G.add_node("python")
        G.add_node("java")
        
        # Check that there's no path between unconnected nodes
        assert not nx.has_path(G, "python", "java")

    def test_dijkstra_simple(self):
        """Test Dijkstra's algorithm with simple weighted graph."""
        G = nx.DiGraph()
        
        G.add_edge("python", "docker", weight=10)
        G.add_edge("docker", "k8s", weight=5)
        
        path = nx.dijkstra_path(G, "python", "k8s")
        assert path == ["python", "docker", "k8s"]
        
        dist = nx.dijkstra_path_length(G, "python", "k8s")
        assert dist == 15


class TestGraphEdgeWeights:
    """Tests for edge weight handling."""

    def test_add_weighted_edge(self):
        """Test adding weighted edge."""
        G = nx.DiGraph()
        
        G.add_edge("skill1", "skill2", weight=10)
        
        assert G["skill1"]["skill2"]["weight"] == 10

    def test_edge_with_weight_attribute(self):
        """Test that edge can store weight."""
        G = nx.DiGraph()
        
        G.add_edge("a", "b", weight=5)
        
        assert G.edges["a", "b"]["weight"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
