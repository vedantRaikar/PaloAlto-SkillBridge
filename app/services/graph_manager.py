import json
import networkx as nx
from pathlib import Path
from typing import List, Dict, Optional
from app.core.config import settings
from app.models.graph import Node, Link, NodeType, LinkType

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
            self._initialize_default_graph()

    def _initialize_default_graph(self):
        nodes = [
            {"id": "frontend_developer", "type": "role", "title": "Frontend Developer"},
            {"id": "backend_developer", "type": "role", "title": "Backend Developer"},
            {"id": "devops_engineer", "type": "role", "title": "DevOps Engineer"},
            {"id": "fullstack_developer", "type": "role", "title": "Full Stack Developer"},
            {"id": "data_scientist", "type": "role", "title": "Data Scientist"},
            {"id": "javascript", "type": "skill", "category": "programming"},
            {"id": "typescript", "type": "skill", "category": "programming"},
            {"id": "react", "type": "skill", "category": "frontend"},
            {"id": "html_css", "type": "skill", "category": "frontend"},
            {"id": "python", "type": "skill", "category": "programming"},
            {"id": "sql", "type": "skill", "category": "database"},
            {"id": "postgresql", "type": "skill", "category": "database"},
            {"id": "docker", "type": "skill", "category": "devops"},
            {"id": "kubernetes", "type": "skill", "category": "devops"},
            {"id": "aws", "type": "skill", "category": "cloud"},
            {"id": "git", "type": "skill", "category": "tools"},
            {"id": "fastapi", "type": "skill", "category": "backend"},
            {"id": "nodejs", "type": "skill", "category": "backend"},
            {"id": "mongodb", "type": "skill", "category": "database"},
            {"id": "machine_learning", "type": "skill", "category": "ai"},
            {"id": "pandas", "type": "skill", "category": "ai"},
            {"id": "course_react_101", "type": "course", "title": "React - The Complete Guide", "provider": "Udemy", "duration_hours": 52},
            {"id": "course_python_101", "type": "course", "title": "Python for Data Science", "provider": "Coursera", "duration_hours": 40},
            {"id": "course_docker_101", "type": "course", "title": "Docker Mastery", "provider": "Udemy", "duration_hours": 20},
            {"id": "course_aws_101", "type": "course", "title": "AWS Certified Solutions Architect", "provider": "AWS Training", "duration_hours": 30},
        ]
        
        links = [
            {"source": "frontend_developer", "target": "javascript", "type": "REQUIRES"},
            {"source": "frontend_developer", "target": "react", "type": "REQUIRES"},
            {"source": "frontend_developer", "target": "html_css", "type": "REQUIRES"},
            {"source": "backend_developer", "target": "python", "type": "REQUIRES"},
            {"source": "backend_developer", "target": "sql", "type": "REQUIRES"},
            {"source": "backend_developer", "target": "fastapi", "type": "REQUIRES"},
            {"source": "devops_engineer", "target": "docker", "type": "REQUIRES"},
            {"source": "devops_engineer", "target": "kubernetes", "type": "REQUIRES"},
            {"source": "devops_engineer", "target": "aws", "type": "REQUIRES"},
            {"source": "devops_engineer", "target": "python", "type": "REQUIRES"},
            {"source": "fullstack_developer", "target": "javascript", "type": "REQUIRES"},
            {"source": "fullstack_developer", "target": "react", "type": "REQUIRES"},
            {"source": "fullstack_developer", "target": "python", "type": "REQUIRES"},
            {"source": "fullstack_developer", "target": "sql", "type": "REQUIRES"},
            {"source": "data_scientist", "target": "python", "type": "REQUIRES"},
            {"source": "data_scientist", "target": "machine_learning", "type": "REQUIRES"},
            {"source": "data_scientist", "target": "pandas", "type": "REQUIRES"},
            {"source": "data_scientist", "target": "sql", "type": "REQUIRES"},
            {"source": "course_react_101", "target": "react", "type": "TEACHES"},
            {"source": "course_python_101", "target": "python", "type": "TEACHES"},
            {"source": "course_docker_101", "target": "docker", "type": "TEACHES"},
            {"source": "course_aws_101", "target": "aws", "type": "TEACHES"},
        ]
        
        for node in nodes:
            self._graph.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
        
        for link in links:
            self._graph.add_edge(link["source"], link["target"], type=link["type"], weight=1.0)
        
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
        self.graph.add_node(node.id, **{k: v for k, v in node.model_dump().items() if k != "id"})

    def add_edge(self, source: str, target: str, link_type: LinkType, weight: float = 1.0):
        self.graph.add_edge(source, target, type=link_type.value, weight=weight)

    def get_role_skills(self, role_id: str) -> List[str]:
        return [t for _, t in self.graph.out_edges(role_id) 
                if self.graph.nodes[t].get('type') == 'skill']

    def get_user_skills(self, user_id: str) -> List[str]:
        return [t for _, t in self.graph.out_edges(user_id)
                if self.graph.nodes[t].get('type') == 'skill']

    def get_courses_for_skill(self, skill_id: str) -> List[Dict]:
        return [{'id': s, **self.graph.nodes[s]} 
                for s, _ in self.graph.in_edges(skill_id)
                if self.graph.nodes[s].get('type') == 'course']

    def get_all_roles(self) -> List[Dict]:
        return [{'id': n, **self.graph.nodes[n]} 
                for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'role']

    def get_all_skills(self) -> List[Dict]:
        return [{'id': n, **self.graph.nodes[n]} 
                for n in self.graph.nodes() 
                if self.graph.nodes[n].get('type') == 'skill']

    def get_shortest_learning_path(self, from_skill: str, to_skill: str) -> List[str]:
        try:
            return nx.shortest_path(self.graph, from_skill, to_skill)
        except nx.NetworkXNoPath:
            return []

    def get_node(self, node_id: str) -> Optional[Dict]:
        if node_id in self.graph.nodes:
            return {'id': node_id, **self.graph.nodes[node_id]}
        return None
