import json
import networkx as nx
from pathlib import Path
from typing import List, Dict, Optional, Set
from app.core.config import settings
from app.models.graph import Node, Link, NodeType, LinkType

CATEGORIES = ['programming', 'frontend', 'backend', 'devops', 'cloud', 'database', 
              'ai', 'tools', 'security', 'mobile', 'api', 'architecture', 
              'data', 'infrastructure', 'quality', 'methodology']


class GraphManager:
    _instance = None
    _graph: Optional[nx.DiGraph] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if GraphManager._graph is None:
            self._load_graph()

    def _load_graph(self) -> nx.DiGraph:
        if settings.KNOWLEDGE_GRAPH_PATH.exists():
            with open(settings.KNOWLEDGE_GRAPH_PATH) as f:
                data = json.load(f)
            GraphManager._graph = nx.node_link_graph(data, directed=True)
        else:
            GraphManager._graph = nx.DiGraph()
            self._initialize_empty_graph()

    def _initialize_empty_graph(self):
        for category in CATEGORIES:
            node_id = f"category_{category}"
            self._graph.add_node(node_id, id=node_id, type="domain", title=category.title())
        
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.save_graph()

    @property
    def graph(self) -> nx.DiGraph:
        return GraphManager._graph

    def save_graph(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(GraphManager._graph)
        with open(settings.KNOWLEDGE_GRAPH_PATH, 'w') as f:
            json.dump(data, f, indent=2)

    def add_node(self, node: Node):
        node_dict = {k: v for k, v in node.model_dump().items() if k != "id"}
        self.graph.add_node(node.id, **node_dict)

    def add_edge(self, source: str, target: str, link_type: LinkType, weight: float = 1.0):
        link_type_str = link_type.value if hasattr(link_type, 'value') else link_type
        self.graph.add_edge(source, target, type=link_type_str, weight=weight)

    def get_role_skills(self, role_id: str) -> List[str]:
        return [t for _, t in self.graph.out_edges(role_id) 
                if self.graph.nodes[t].get('type') == 'skill']

    def get_user_skills(self, user_id: str) -> List[str]:
        return [t for _, t in self.graph.out_edges(user_id)
                if self.graph.nodes[t].get('type') == 'skill']

    def get_courses_for_skill(self, skill_id: str) -> List[Dict]:
        return [{'id': t, **self.graph.nodes[t]} 
                for _, t in self.graph.out_edges(skill_id)
                if self.graph.nodes[t].get('type') == 'course']

    def get_all_roles(self) -> List[Dict]:
        return [{'id': n, **self.graph.nodes[n]} 
                for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'role']

    def get_all_skills(self) -> List[Dict]:
        return [{'id': n, **self.graph.nodes[n]} 
                for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'skill']

    def get_all_courses(self) -> List[Dict]:
        return [{'id': n, **self.graph.nodes[n]} 
                for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'course']

    def get_skills_by_category(self, category: str) -> List[str]:
        return [n for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'skill' 
                and self.graph.nodes[n].get('category') == category]

    def get_shortest_learning_path(self, from_skill: str, to_skill: str) -> List[str]:
        try:
            return nx.shortest_path(self.graph, from_skill, to_skill)
        except nx.NetworkXNoPath:
            return []

    def get_node(self, node_id: str) -> Optional[Dict]:
        if node_id in self.graph.nodes:
            return {'id': node_id, **self.graph.nodes[node_id]}
        return None

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.graph.nodes

    def get_node_type(self, node_id: str) -> Optional[str]:
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id].get('type')
        return None

    def get_related_skills(self, skill_id: str) -> List[str]:
        related = []
        for s, t, data in self.graph.edges(data=True):
            if s == skill_id and data.get('type') == 'RELATED_TO':
                related.append(t)
            if t == skill_id and data.get('type') == 'RELATED_TO':
                related.append(s)
        return related

    def get_skill_category(self, skill_id: str) -> Optional[str]:
        if skill_id in self.graph.nodes:
            return self.graph.nodes[skill_id].get('category')
        return None

    def add_skill_with_category(self, skill_id: str, category: str, title: Optional[str] = None):
        if not self.node_exists(skill_id):
            node = Node(
                id=skill_id,
                type=NodeType.SKILL,
                category=category,
                title=title or skill_id.replace('_', ' ').title()
            )
            self.add_node(node)
            
            category_node = f"category_{category}"
            if self.node_exists(category_node):
                self.add_edge(category_node, skill_id, LinkType.PART_OF)

    def add_role_with_skills(self, role_id: str, skill_ids: List[str], title: Optional[str] = None):
        if not self.node_exists(role_id):
            node = Node(
                id=role_id,
                type=NodeType.ROLE,
                title=title or role_id.replace('_', ' ').title()
            )
            self.add_node(node)
        
        for skill_id in skill_ids:
            if not self.node_exists(skill_id):
                self.add_skill_with_category(skill_id, "programming")
            
            if not self.graph.has_edge(role_id, skill_id):
                self.add_edge(role_id, skill_id, LinkType.REQUIRES)

    def add_course_with_skills(self, course_id: str, skill_ids: List[str], title: str, provider: Optional[str] = None):
        if not self.node_exists(course_id):
            node = Node(
                id=course_id,
                type=NodeType.COURSE,
                title=title,
                metadata={'provider': provider} if provider else {}
            )
            self.add_node(node)
        
        for skill_id in skill_ids:
            if not self.node_exists(skill_id):
                self.add_skill_with_category(skill_id, "programming")
            
            if not self.graph.has_edge(course_id, skill_id):
                self.add_edge(course_id, skill_id, LinkType.TEACHES)

    def remove_node(self, node_id: str):
        if node_id in self.graph.nodes:
            self.graph.remove_node(node_id)

    def remove_edge(self, source: str, target: str):
        if self.graph.has_edge(source, target):
            self.graph.remove_edge(source, target)

    def get_graph_stats(self) -> Dict:
        nodes = list(self.graph.nodes())
        return {
            'total_nodes': len(nodes),
            'roles': len([n for n in nodes if self.graph.nodes[n].get('type') == 'role']),
            'skills': len([n for n in nodes if self.graph.nodes[n].get('type') == 'skill']),
            'courses': len([n for n in nodes if self.graph.nodes[n].get('type') == 'course']),
            'total_edges': self.graph.number_of_edges(),
            'categories': list(set(self.graph.nodes[n].get('category') for n in nodes 
                                  if self.graph.nodes[n].get('category')))
        }
