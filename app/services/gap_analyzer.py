from typing import List, Dict
from app.services.graph_manager import GraphManager
from app.models.user import SkillGap
from app.services.knowledge_sources.onet_integration import get_skill_mapper

class GapAnalyzer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.graph_manager = GraphManager()
        self._course_cache: Dict[str, List[Dict]] = {}
        self._cert_cache: Dict[str, List[Dict]] = {}
        self._skill_mapper = None
        self._initialized = True
    
    @property
    def skill_mapper(self):
        if self._skill_mapper is None:
            self._skill_mapper = get_skill_mapper()
        return self._skill_mapper

    def analyze_gaps(self, user_id: str, target_role: str) -> SkillGap:
        required_skills = self.graph_manager.get_role_skills(target_role)
        user_skills = self.graph_manager.get_user_skills(user_id)
        
        gaps = [s for s in required_skills if s not in user_skills]
        matched = [s for s in required_skills if s in user_skills]
        
        gap_courses = {}
        gap_certifications = {}
        
        for gap in gaps:
            courses = self._get_cached_courses(gap)
            certs = self._get_cached_certs(gap)
            gap_courses[gap] = courses
            gap_certifications[gap] = certs
        
        return SkillGap(
            user_id=user_id,
            target_role=target_role,
            matched_skills=matched,
            missing_skills=gaps,
            courses_for_gaps=gap_courses,
            certifications_for_gaps=gap_certifications,
        )

    def _get_cached_courses(self, skill_id: str) -> List[Dict]:
        if skill_id in self._course_cache:
            return self._course_cache[skill_id]
        
        graph_courses = self.graph_manager.get_courses_for_skill(skill_id)
        
        if graph_courses:
            self._course_cache[skill_id] = graph_courses
            return graph_courses
        
        courses = self._fetch_courses_web(skill_id)
        self._course_cache[skill_id] = courses
        
        if courses:
            self._store_courses_in_graph(skill_id, courses)
        
        return courses

    def _get_cached_certs(self, skill_id: str) -> List[Dict]:
        if skill_id in self._cert_cache:
            return self._cert_cache[skill_id]
        
        cert_nodes = []
        for _, cert_id in self.graph_manager.graph.out_edges(skill_id):
            node_data = self.graph_manager.graph.nodes[cert_id]
            if node_data.get('type') == 'certification':
                cert_nodes.append({**node_data, 'id': cert_id})
        
        if cert_nodes:
            self._cert_cache[skill_id] = cert_nodes
            return cert_nodes
        
        certs = self._fetch_certs_web(skill_id)
        self._cert_cache[skill_id] = certs
        
        if certs:
            self._store_certs_in_graph(skill_id, certs)
        
        return certs

    def _fetch_courses_web(self, skill_id: str) -> List[Dict]:
        try:
            return self.skill_mapper.get_learning_path(skill_id)
        except Exception:
            return []

    def _fetch_certs_web(self, skill_id: str) -> List[Dict]:
        try:
            from app.services.cert_discovery.service import get_certification_service
            cert_service = get_certification_service()
            certs = cert_service.get_by_skill(skill_id)
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "provider": c.provider,
                    "certification_url": c.certification_url,
                    "level": c.level,
                    "cost_usd": c.cost_usd,
                }
                for c in certs
            ]
        except Exception:
            return []

    def _store_courses_in_graph(self, skill_id: str, courses: List[Dict]):
        try:
            from app.models.graph import Node, NodeType, LinkType
            
            for c in courses:
                course_id = f"{c.get('provider', 'course')}_{c.get('title', skill_id)[:30].replace(' ', '_').lower()}"
                
                if not self.graph_manager.get_node(course_id):
                    course_node = Node(
                        id=course_id,
                        type=NodeType.COURSE,
                        title=c.get("title", skill_id),
                        category=c.get("provider", "unknown"),
                        metadata={
                            "provider": c.get("provider", ""),
                            "url": c.get("url", ""),
                            "instructor": c.get("instructor", ""),
                            "duration_hours": c.get("duration_hours"),
                            "rating": c.get("rating"),
                            "level": c.get("level", "all"),
                        }
                    )
                    self.graph_manager.add_node(course_node)
                    self.graph_manager.add_edge(skill_id, course_id, LinkType.TEACHES)
            
            self.graph_manager.save_graph()
        except Exception:
            pass

    def _store_certs_in_graph(self, skill_id: str, certs: List[Dict]):
        try:
            from app.models.graph import Node, NodeType, LinkType
            
            for c in certs:
                cert_id = f"cert_{c.get('id', c.get('name', skill_id)[:30].replace(' ', '_').lower())}"
                
                if not self.graph_manager.get_node(cert_id):
                    cert_node = Node(
                        id=cert_id,
                        type=NodeType.CERTIFICATION,
                        title=c.get("name", skill_id),
                        category=c.get("provider", "unknown"),
                        metadata={
                            "provider": c.get("provider", ""),
                            "level": c.get("level", "associate"),
                            "cost_usd": c.get("cost_usd"),
                            "certification_url": c.get("certification_url", ""),
                        }
                    )
                    self.graph_manager.add_node(cert_node)
                    self.graph_manager.add_edge(skill_id, cert_id, LinkType.TEACHES)
            
            self.graph_manager.save_graph()
        except Exception:
            pass

    def get_role_requirements(self, target_role: str) -> Dict:
        skills = self.graph_manager.get_role_skills(target_role)
        skill_details = []
        for skill in skills:
            node = self.graph_manager.get_node(skill)
            if node:
                skill_details.append(node)
        
        return {
            "role": target_role,
            "required_skills": skills,
            "skill_details": skill_details,
            "total_skills_required": len(skills)
        }

    def calculate_readiness_score(self, user_id: str, target_role: str) -> float:
        required_skills = self.graph_manager.get_role_skills(target_role)
        user_skills = self.graph_manager.get_user_skills(user_id)
        
        if not required_skills:
            return 0.0
        
        matched = len([s for s in required_skills if s in user_skills])
        return round((matched / len(required_skills)) * 100, 1)
    
    def get_courses_for_skill(self, skill_id: str, max_results: int = 5) -> List[Dict]:
        if skill_id in self._course_cache:
            return self._course_cache[skill_id][:max_results]
        
        courses = self.graph_manager.get_courses_for_skill(skill_id)
        if courses:
            self._course_cache[skill_id] = courses
            return courses[:max_results]
        
        courses = self._fetch_courses_web(skill_id)
        self._course_cache[skill_id] = courses
        return courses[:max_results]
    
    def get_certifications_for_skill(self, skill_id: str) -> List[Dict]:
        if skill_id in self._cert_cache:
            return self._cert_cache[skill_id]
        
        cert_nodes = []
        for _, cert_id in self.graph_manager.graph.out_edges(skill_id):
            node_data = self.graph_manager.graph.nodes[cert_id]
            if node_data.get('type') == 'certification':
                cert_nodes.append({**node_data, 'id': cert_id})
        
        if cert_nodes:
            self._cert_cache[skill_id] = cert_nodes
            return cert_nodes
        
        certs = self._fetch_certs_web(skill_id)
        self._cert_cache[skill_id] = certs
        return certs
