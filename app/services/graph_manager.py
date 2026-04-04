import json
import networkx as nx
from pathlib import Path
from typing import List, Dict, Optional, Set
from app.core.config import settings
from app.core.logger import get_logger
from app.models.graph import Node, Link, NodeType, LinkType

CATEGORIES = ['programming', 'frontend', 'backend', 'devops', 'cloud', 'database', 
              'ai', 'tools', 'security', 'mobile', 'api', 'architecture', 
              'data', 'infrastructure', 'quality', 'methodology']

logger = get_logger(__name__)


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

    def _normalize_skill_id(self, skill_id: str) -> str:
        return (skill_id or "").strip().lower().replace(" ", "_").replace("-", "_")

    def _has_outgoing_resource(self, skill_id: str, node_type: str) -> bool:
        if skill_id not in self.graph.nodes:
            return False
        for _, target in self.graph.out_edges(skill_id):
            if self.graph.nodes[target].get("type") == node_type:
                return True
        return False

    def ensure_skill_node(
        self,
        skill_id: str,
        category: str = "programming",
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
        enrich_resources: bool = False,
        force_refresh: bool = False,
    ) -> str:
        normalized_skill_id = self._normalize_skill_id(skill_id)
        if not normalized_skill_id:
            return normalized_skill_id

        if not self.node_exists(normalized_skill_id):
            node = Node(
                id=normalized_skill_id,
                type=NodeType.SKILL,
                category=category,
                title=title or normalized_skill_id.replace('_', ' ').title(),
                metadata=metadata or {},
            )
            self.add_node(node)

        category_node = f"category_{category}"
        if self.node_exists(category_node) and not self.graph.has_edge(category_node, normalized_skill_id):
            self.add_edge(category_node, normalized_skill_id, LinkType.PART_OF)

        if enrich_resources:
            self.enrich_skill_resources(normalized_skill_id, force_refresh=force_refresh)

        return normalized_skill_id

    def add_user_skill(
        self,
        user_id: str,
        skill_id: str,
        category: str = "programming",
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
        enrich_resources: bool = True,
        force_refresh: bool = False,
    ) -> Optional[str]:
        normalized_skill_id = self.ensure_skill_node(
            skill_id,
            category=category,
            title=title,
            metadata=metadata,
            enrich_resources=enrich_resources,
            force_refresh=force_refresh,
        )
        if not normalized_skill_id:
            return None

        if not self.graph.has_edge(user_id, normalized_skill_id):
            self.add_edge(user_id, normalized_skill_id, LinkType.HAS_SKILL)

        return normalized_skill_id

    def store_courses_for_skill(self, skill_id: str, courses: List[Dict]) -> bool:
        normalized_skill_id = self._normalize_skill_id(skill_id)
        added = False

        for course in courses:
            course_id = f"{course.get('provider', 'course')}_{course.get('title', normalized_skill_id)[:30].replace(' ', '_').lower()}"
            if not self.get_node(course_id):
                course_node = Node(
                    id=course_id,
                    type=NodeType.COURSE,
                    title=course.get("title", normalized_skill_id),
                    category=course.get("provider", "unknown"),
                    metadata={
                        "provider": course.get("provider", ""),
                        "url": course.get("url", ""),
                        "instructor": course.get("instructor", ""),
                        "duration_hours": course.get("duration_hours"),
                        "rating": course.get("rating"),
                        "level": course.get("level", "all"),
                        "source": course.get("source", course.get("provider", "")),
                    },
                )
                self.add_node(course_node)
                added = True

            if not self.graph.has_edge(normalized_skill_id, course_id):
                self.add_edge(normalized_skill_id, course_id, LinkType.TEACHES)
                added = True

        return added

    def store_certifications_for_skill(self, skill_id: str, certs: List[Dict]) -> bool:
        normalized_skill_id = self._normalize_skill_id(skill_id)
        added = False

        for cert in certs:
            cert_id = f"cert_{cert.get('id', cert.get('name', normalized_skill_id)[:30].replace(' ', '_').lower())}"
            if not self.get_node(cert_id):
                cert_node = Node(
                    id=cert_id,
                    type=NodeType.CERTIFICATION,
                    title=cert.get("name", normalized_skill_id),
                    category=cert.get("provider", "unknown"),
                    metadata={
                        "provider": cert.get("provider", ""),
                        "level": cert.get("level", "associate"),
                        "cost_usd": cert.get("cost_usd"),
                        "certification_url": cert.get("certification_url", ""),
                    },
                )
                self.add_node(cert_node)
                added = True

            if not self.graph.has_edge(normalized_skill_id, cert_id):
                self.add_edge(normalized_skill_id, cert_id, LinkType.TEACHES)
                added = True

        return added

    def enrich_skill_resources(self, skill_id: str, force_refresh: bool = False):
        normalized_skill_id = self._normalize_skill_id(skill_id)
        if not normalized_skill_id or not self.node_exists(normalized_skill_id):
            return

        try:
            if force_refresh or not self._has_outgoing_resource(normalized_skill_id, NodeType.COURSE.value):
                from app.services.knowledge_sources.onet_integration import get_skill_mapper

                courses = get_skill_mapper().get_learning_path(normalized_skill_id, prefer_live=True)
                if courses:
                    self.store_courses_for_skill(normalized_skill_id, courses)
        except Exception as exc:
            logger.warning(
                "Skill course enrichment failed",
                extra={"skill_id": normalized_skill_id, "force_refresh": force_refresh, "error": str(exc)},
            )

        try:
            if force_refresh or not self._has_outgoing_resource(normalized_skill_id, NodeType.CERTIFICATION.value):
                from app.services.cert_discovery.service import get_certification_service

                cert_service = get_certification_service()
                certs = cert_service.get_by_skill(normalized_skill_id)
                mapped_certs = [
                    {
                        "id": cert.id,
                        "name": cert.name,
                        "provider": cert.provider,
                        "certification_url": cert.certification_url,
                        "level": cert.level,
                        "cost_usd": cert.cost_usd,
                    }
                    for cert in certs
                ]
                if mapped_certs:
                    self.store_certifications_for_skill(normalized_skill_id, mapped_certs)
        except Exception as exc:
            logger.warning(
                "Skill certification enrichment failed",
                extra={"skill_id": normalized_skill_id, "force_refresh": force_refresh, "error": str(exc)},
            )

    def refresh_skill_resources(self, skill_id: str):
        """Force-refresh skill resources even if course/cert edges already exist."""
        self.enrich_skill_resources(skill_id, force_refresh=True)

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

    def populate_skill_prerequisites(
        self,
        skills: List[str],
        prerequisites_map: Dict[str, List[str]],
        duration_map: Dict[str, float],
    ) -> None:
        """Wire weighted PREREQUISITE_FOR edges between skill nodes.

        Edge direction: prereq ──PREREQUISITE_FOR──▶ skill
        Edge weight   : duration_hours of the *target* skill (learning cost to traverse)

        This lets nx.multi_source_dijkstra find the minimum-time prerequisite chain
        from any set of already-known skills to each missing skill.
        """
        for skill in skills:
            skill_norm = self._normalize_skill_id(skill)
            duration = duration_map.get(skill_norm, 20.0)

            # Store duration as a node attribute so it survives graph serialisation.
            if self.node_exists(skill_norm):
                self.graph.nodes[skill_norm]["duration_hours"] = duration
            else:
                node = Node(
                    id=skill_norm,
                    type=NodeType.SKILL,
                    title=skill_norm.replace("_", " ").title(),
                )
                self.add_node(node)
                self.graph.nodes[skill_norm]["duration_hours"] = duration

            prereqs = prerequisites_map.get(skill_norm, [])
            for prereq in prereqs:
                prereq_norm = self._normalize_skill_id(prereq)
                if not self.node_exists(prereq_norm):
                    prereq_duration = duration_map.get(prereq_norm, 20.0)
                    prereq_node = Node(
                        id=prereq_norm,
                        type=NodeType.SKILL,
                        title=prereq_norm.replace("_", " ").title(),
                    )
                    self.add_node(prereq_node)
                    self.graph.nodes[prereq_norm]["duration_hours"] = prereq_duration
                # Only add edge if not already present; preserve existing weight.
                if not self.graph.has_edge(prereq_norm, skill_norm):
                    self.add_edge(prereq_norm, skill_norm, LinkType.PREREQUISITE_FOR, weight=duration)

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
        self.ensure_skill_node(skill_id, category=category, title=title)

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
