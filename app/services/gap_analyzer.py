from typing import List, Dict, Set
from app.services.graph_manager import GraphManager
from app.models.user import SkillGap
from app.services.knowledge_sources.onet_integration import get_skill_mapper, SKILL_ALIASES
from app.services.similarity.semantic_matcher import get_semantic_matcher
from app.services.learning_path_generator import get_learning_path_generator
from app.services.fast_track_generator import get_fast_track_generator
from app.services.optimized_path_generator import get_optimized_path_generator

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
        self._skill_alias_map: Dict[str, Set[str]] = {}
        self._semantic_matcher = None
        self._initialized = True
        self._build_alias_map()
    
    def _build_alias_map(self):
        """Build bidirectional alias mapping for skills"""
        for skill, aliases in SKILL_ALIASES.items():
            self._skill_alias_map[skill.lower()] = {a.lower() for a in aliases}
            for alias in aliases:
                if alias.lower() not in self._skill_alias_map:
                    self._skill_alias_map[alias.lower()] = set()
                self._skill_alias_map[alias.lower()].add(skill.lower())
    
    @property
    def semantic_matcher(self):
        """Lazy load semantic matcher for better skill matching"""
        if self._semantic_matcher is None:
            self._semantic_matcher = get_semantic_matcher()
        return self._semantic_matcher
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name to canonical form"""
        normalized = skill.lower().strip().replace(" ", "_").replace("-", "_")
        return normalized
    
    def _skills_match(self, skill1: str, skill2: str) -> bool:
        """
        Check if two skills match using semantic similarity.
        Uses multiple strategies for best accuracy:
        1. Exact match (fastest)
        2. Alias match
        3. Substring match
        4. Semantic similarity (most accurate)
        """
        s1 = self._normalize_skill(skill1)
        s2 = self._normalize_skill(skill2)
        
        if s1 == s2:
            return True
        
        if s1 in self._skill_alias_map.get(s2, set()):
            return True
        if s2 in self._skill_alias_map.get(s1, set()):
            return True
        
        try:
            return self.semantic_matcher.skills_match(skill1, skill2)
        except Exception:
            return False
    
    @property
    def skill_mapper(self):
        if self._skill_mapper is None:
            self._skill_mapper = get_skill_mapper()
        return self._skill_mapper
    
    def _get_role_skills(self, target_role: str) -> List[str]:
        """Get skills for a role from graph or O*NET fallback."""
        graph_skills = self.graph_manager.get_role_skills(target_role)
        if graph_skills:
            return graph_skills
        
        from app.services.knowledge_sources.onet_integration import get_onet_knowledge
        onet = get_onet_knowledge()
        onet_skills = onet.get_skills_for_occupation(target_role)
        if onet_skills:
            return onet_skills
        
        return []

    def analyze_gaps(self, user_id: str, target_role: str) -> SkillGap:
        required_skills = self._get_role_skills(target_role)
        user_skills = self.graph_manager.get_user_skills(user_id)
        
        if not user_skills:
            from app.services.knowledge_sources.onet_integration import get_onet_knowledge
            onet = get_onet_knowledge()
            all_known_skills = []
            for occ in onet.get_all_occupations():
                all_known_skills.extend(occ.get('skills', []))
            user_skills = [s for s in all_known_skills if any(self._skills_match(s, us) for us in user_skills)]
        
        gaps = [s for s in required_skills if not any(self._skills_match(s, us) for us in user_skills)]
        matched = [s for s in required_skills if any(self._skills_match(s, us) for us in user_skills)]
        
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

    def get_ordered_learning_path(self, user_id: str, target_role: str) -> Dict:
        """
        Get an ordered learning path for reaching the target role.
        Uses topological sort based on skill prerequisites.
        
        Returns:
            {
                "ordered_skills": [...],  # Skills in learning order
                "phases": {
                    "foundation": [...],     # Start here
                    "intermediate": [...],
                    "advanced": [...]
                },
                "milestones": {...},        # Learning milestones per skill
                "estimated_days": int,
                "estimated_weeks": float,
            }
        """
        user_skills = self.graph_manager.get_user_skills(user_id)
        required_skills = self._get_role_skills(target_role)
        
        gaps = [s for s in required_skills if not any(self._skills_match(s, us) for us in user_skills)]
        
        path_generator = get_learning_path_generator()
        learning_path = path_generator.generate_learning_path(gaps, user_skills)
        
        skills_with_resources = {}
        for skill in learning_path["ordered_skills"]:
            courses = self._get_cached_courses(skill)
            certs = self._get_cached_certs(skill)
            skills_with_resources[skill] = {
                "skill": skill,
                "level": path_generator.get_skill_level(skill),
                "category": path_generator.get_skill_category(skill),
                "prerequisites": learning_path["prerequisites"].get(skill, []),
                "courses": courses[:3],
                "certifications": certs[:2],
            }
        
        return {
            "target_role": target_role,
            "user_skills": user_skills,
            "ordered_skills": learning_path["ordered_skills"],
            "phases": learning_path["phases"],
            "milestones": skills_with_resources,
            "total_skills_to_learn": learning_path["total_skills_to_learn"],
            "estimated_days": learning_path["estimated_days"],
            "estimated_weeks": learning_path["estimated_weeks"],
            "category_breakdown": learning_path["category_breakdown"],
        }

    def get_fast_track_path(
        self,
        user_id: str,
        target_role: str,
        max_skills: int = 5
    ) -> Dict:
        """
        Get the fastest path to job readiness.
        Prioritizes essential skills and quick courses.
        
        Returns:
            {
                "type": "fast_track",
                "target_role": str,
                "user_skills": [...],
                "fast_track_skills": [...],
                "skill_details": [...],
                "current_readiness": float,
                "projected_readiness": float,
                "total_hours": int,
                "total_weeks": float,
                "study_plan": [...]
            }
        """
        user_skills = self.graph_manager.get_user_skills(user_id)
        required_skills = self._get_role_skills(target_role)
        
        if not user_skills:
            user_skills = []
        
        fast_track_gen = get_fast_track_generator()
        return fast_track_gen.generate_fast_track(
            user_skills=user_skills,
            target_role=target_role,
            all_role_skills=required_skills,
            max_skills_to_learn=max_skills
        )

    def get_optimized_paths(
        self,
        user_id: str,
        target_role: str
    ) -> Dict:
        """
        Get optimized learning paths using Dijkstra's algorithm.
        
        Uses graph shortest path algorithms to find:
        1. Fastest path (minimum time)
        2. Most impactful path (highest job market value)
        3. Most efficient path (best impact per hour)
        
        Returns:
            {
                "paths": [...],
                "recommendation": {...},
                "analysis": {...}
            }
        """
        user_skills = self.graph_manager.get_user_skills(user_id)
        required_skills = self._get_role_skills(target_role)
        
        if not user_skills:
            user_skills = []
        
        user_skill_set = set(s.lower().replace(" ", "_").replace("-", "_") for s in user_skills)
        
        missing_skills = [
            s for s in required_skills
            if s.lower().replace(" ", "_").replace("-", "_") not in user_skill_set
        ]
        
        optimized_gen = get_optimized_path_generator()
        return optimized_gen.generate_optimized_paths(
            user_skills=user_skills,
            target_role=target_role,
            all_role_skills=required_skills,
            missing_skills=missing_skills
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
