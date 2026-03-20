import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from app.core.logger import get_logger
from app.models.course import Course, CourseSearchRequest, CourseSearchResponse, CourseDiscoverRequest, CourseDiscoverResponse
from app.models.certification import Certification, CertificationSearchRequest, CertificationSearchResponse
from app.services.graph_manager import GraphManager
from app.services.course_discovery import get_course_aggregator
from app.services.cert_discovery import get_certification_service
from app.models.graph import Node, Link, NodeType, LinkType

logger = get_logger(__name__)

class LearningResourceManager:
    def __init__(self):
        self.gm = GraphManager()
        self.course_aggregator = get_course_aggregator()
        self.cert_service = get_certification_service()
        self._load_cached_resources()
    
    def _load_cached_resources(self):
        self.cached_courses = self._load_json("data/learning_resources/courses.json") or []
        self.cached_certs = self._load_json("data/learning_resources/certifications.json") or []
        self.resource_map = self._load_json("data/learning_resources/resource_map.json") or {}
    
    def _load_json(self, path: str) -> Optional[Dict]:
        p = Path(path)
        if p.exists():
            with open(p) as f:
                return json.load(f)
        return None
    
    def _save_json(self, path: str, data: Any):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def search_courses(self, request: CourseSearchRequest) -> CourseSearchResponse:
        response = await self.course_aggregator.search_all(
            skill=request.skill,
            providers=request.providers,
            max_results=request.max_results,
            free_only=request.free_only,
            min_rating=request.min_rating,
        )
        
        for course in response.courses:
            self._add_course_to_graph(course)
        
        self._cache_courses(response.courses)
        
        return response
    
    async def discover_courses_for_skills(self, request: CourseDiscoverRequest) -> CourseDiscoverResponse:
        courses_by_skill = {}
        recommended_paths = []

        async def _search_skill(skill: str):
            try:
                response = await self.course_aggregator.search_all(
                    skill=skill,
                    max_results=request.max_courses_per_skill,
                    free_only=request.budget == "free",
                    providers=request.preferred_providers,
                )
                courses = response.courses
                if request.budget == "paid":
                    courses = [c for c in courses if not c.is_free]
                return skill, courses
            except Exception as e:
                logger.exception("Error discovering courses for skill %s", skill)
                return skill, []

        results = await asyncio.gather(*[_search_skill(s) for s in request.skills])

        all_courses = []
        for skill, courses in results:
            courses_by_skill[skill] = courses
            all_courses.extend(courses)

        # Batch graph additions — save once at the end
        any_added = False
        for course in all_courses:
            if not self.gm.get_node(course.id):
                self._add_course_to_graph_nosave(course)
                any_added = True
        if any_added:
            self.gm.save_graph()
        
        recommended_paths = self._generate_learning_paths(request.skills)
        
        all_courses = []
        for skill_courses in courses_by_skill.values():
            all_courses.extend(skill_courses)
        
        self._cache_courses(all_courses)
        
        return CourseDiscoverResponse(
            courses_by_skill={k: v for k, v in courses_by_skill.items() if v},
            recommended_paths=recommended_paths,
            total_courses=len(all_courses),
        )
    
    def search_certifications(
        self,
        skill: Optional[str] = None,
        provider: Optional[str] = None,
        level: Optional[str] = None,
    ) -> CertificationSearchResponse:
        response = self.cert_service.search(
            skill=skill,
            provider=provider,
            level=level,
        )
        
        for cert in response.certifications:
            self._add_certification_to_graph(cert)
        
        self._cache_certifications(response.certifications)
        
        return response
    
    def recommend_certifications_for_skills(self, skills: List[str]) -> List[Dict]:
        certs = self.cert_service.recommend_for_skills(skills)
        
        recommendations = []
        for cert in certs:
            self._add_certification_to_graph(cert)
            
            career_path = self.cert_service.get_career_path(cert.id)
            prereqs = self.cert_service.get_prerequisites(cert.id)
            
            recommendations.append({
                "certification": cert.model_dump(),
                "matched_skills": getattr(cert, "matched_skills", []),
                "skill_match_count": getattr(cert, "skill_match_count", 0),
                "match_ratio": getattr(cert, "match_ratio", 0),
                "career_path": [c.model_dump() for c in career_path],
                "prerequisites": [p.model_dump() for p in prereqs],
            })
        
        self._cache_certifications(certs)
        
        return recommendations
    
    def get_learning_resources_for_skill(self, skill_id: str) -> Dict[str, List]:
        courses = self._search_courses_for_skill(skill_id)
        certifications = []
        
        try:
            certifications = self.cert_service.get_by_skill(skill_id)
        except Exception:
            pass
        
        courses_data = []
        for c in courses:
            if hasattr(c, 'model_dump'):
                courses_data.append(c.model_dump())
            elif isinstance(c, dict):
                courses_data.append(c)
            else:
                courses_data.append({"title": str(c), "provider": "unknown"})
        
        certs_data = []
        for c in certifications:
            if hasattr(c, 'model_dump'):
                certs_data.append(c.model_dump())
            elif isinstance(c, dict):
                certs_data.append(c)
            else:
                certs_data.append({"name": str(c), "provider": "unknown"})
        
        return {
            "skill_id": skill_id,
            "courses": courses_data,
            "certifications": certs_data,
            "total_resources": len(courses_data) + len(certs_data),
        }
    
    def _search_courses_for_skill(self, skill_id: str) -> List[Course]:
        try:
            from app.services.course_discovery.aggregator import get_course_aggregator
            agg = get_course_aggregator()
            result = agg.search(skill_id, max_results=5)
            return result.courses
        except Exception as e:
            logger.exception("Error searching courses for skill %s", skill_id)
            return []
    
    def _add_course_to_graph_nosave(self, course: Course) -> str:
        """Add course to graph without saving (caller must save)."""
        course_id = course.id
        course_node = Node(
            id=course_id,
            type=NodeType.COURSE,
            title=course.title,
            category=course.provider,
            metadata={
                "provider": course.provider,
                "url": course.url,
                "instructor": course.instructor,
                "duration_hours": course.duration_hours,
                "rating": course.rating,
                "num_students": course.num_students,
                "price": course.price if not course.is_free else 0,
                "is_free": course.is_free,
                "level": course.level,
                "thumbnail_url": course.thumbnail_url,
                "skills_taught": course.skills_taught,
            }
        )
        self.gm.add_node(course_node)

        for skill_id in course.skills_taught or []:
            if not self.gm.get_node(skill_id):
                skill_node = Node(
                    id=skill_id,
                    type=NodeType.SKILL,
                    title=skill_id.replace("_", " ").title(),
                )
                self.gm.add_node(skill_node)
            if not self.gm.graph.has_edge(course_id, skill_id):
                self.gm.add_edge(course_id, skill_id, LinkType.TEACHES)

        provider_id = f"provider_{course.provider}"
        if not self.gm.get_node(provider_id):
            try:
                provider_node = Node(
                    id=provider_id,
                    type=NodeType.PROVIDER if hasattr(NodeType, 'PROVIDER') else NodeType.COURSE,
                    title=course.provider.title(),
                )
                self.gm.add_node(provider_node)
            except:
                pass
        if not self.gm.graph.has_edge(provider_id, course_id):
            try:
                self.gm.add_edge(provider_id, course_id, LinkType.TEACHES)
            except:
                pass
        return course_id

    def _add_course_to_graph(self, course: Course) -> str:
        course_id = course.id
        
        if not self.gm.get_node(course_id):
            self._add_course_to_graph_nosave(course)
            self.gm.save_graph()
        
        return course_id
    
    def _add_certification_to_graph(self, cert: Certification) -> str:
        cert_id = f"cert_{cert.id}"
        
        if not self.gm.get_node(cert_id):
            cert_node = Node(
                id=cert_id,
                type=NodeType.CERTIFICATION,
                title=cert.name,
                category=cert.provider,
                metadata={
                    "provider": cert.provider,
                    "url": cert.certification_url,
                    "level": cert.level,
                    "cost_usd": cert.cost_usd,
                    "validity_years": cert.validity_years,
                    "renewal_required": cert.renewal.required,
                    "skills_covered": cert.skills_covered,
                    "prerequisites": cert.prerequisites,
                }
            )
            self.gm.add_node(cert_node)
            
            for skill_id in cert.skills_covered or []:
                if not self.gm.get_node(skill_id):
                    skill_node = Node(
                        id=skill_id,
                        type=NodeType.SKILL,
                        title=skill_id.replace("_", " ").title(),
                    )
                    self.gm.add_node(skill_node)
                
                if not self.gm.graph.has_edge(cert_id, skill_id):
                    self.gm.add_edge(cert_id, skill_id, LinkType.TEACHES)
            
            for prereq_id in cert.prerequisites or []:
                prereq_cert_id = f"cert_{prereq_id}"
                if self.gm.get_node(prereq_cert_id):
                    if not self.gm.graph.has_edge(prereq_cert_id, cert_id):
                        self.gm.add_edge(prereq_cert_id, cert_id, LinkType.PREREQUISITE_FOR)
            
            self.gm.save_graph()
        
        return cert_id
    
    def _get_courses_for_skill(self, skill_id: str) -> List[Course]:
        if skill_id not in self.gm.graph.nodes:
            return []
        
        courses = []
        predecessors = list(self.gm.graph.predecessors(skill_id))
        
        for pred in predecessors:
            node_data = self.gm.graph.nodes[pred]
            if node_data.get("type") == "course":
                course_data = node_data.copy()
                course_data["id"] = pred
                try:
                    courses.append(Course(**course_data))
                except:
                    pass
        
        return courses
    
    def _generate_learning_paths(self, skills: List[str]) -> List[Dict]:
        paths = []
        
        skill_certs = {}
        for skill in skills:
            certs = self.cert_service.get_by_skill(skill)
            if certs:
                skill_certs[skill] = certs
        
        if skill_certs:
            primary_skill = list(skill_certs.keys())[0]
            primary_certs = skill_certs[primary_skill]
            
            if primary_certs:
                best_cert = primary_certs[0]
                career_path = self.cert_service.get_career_path(best_cert.id)
                
                paths.append({
                    "name": f"{best_cert.name} Learning Path",
                    "description": f"Structured path to achieve {best_cert.name}",
                    "steps": [
                        {
                            "type": "certification",
                            "id": cert.id,
                            "name": cert.name,
                            "level": cert.level,
                        }
                        for cert in career_path
                    ],
                    "total_estimated_hours": 40 * len(career_path),
                    "prerequisites": best_cert.prerequisites,
                })
        
        paths.append({
            "name": f"Multi-Skill Learning Path",
            "description": f"Learning path covering: {', '.join(skills)}",
            "steps": [
                {
                    "type": "skill",
                    "id": skill,
                    "name": skill.replace("_", " ").title(),
                }
                for skill in skills
            ],
            "estimated_hours_per_skill": 20,
        })
        
        return paths
    
    def _cache_courses(self, courses: List[Course]):
        cached_data = {
            "courses": [c.model_dump() for c in courses],
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._save_json("data/learning_resources/courses.json", cached_data)
    
    def _cache_certifications(self, certifications: List[Certification]):
        cached_data = {
            "certifications": [c.model_dump() for c in certifications],
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._save_json("data/learning_resources/certifications.json", cached_data)
    
    def get_graph_stats(self) -> Dict:
        total_nodes = self.gm.graph.number_of_nodes()
        total_edges = self.gm.graph.number_of_edges()
        
        course_nodes = [n for n, d in self.gm.graph.nodes(data=True) if d.get("type") == "course"]
        cert_nodes = [n for n, d in self.gm.graph.nodes(data=True) if d.get("type") == "certification"]
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "course_count": len(course_nodes),
            "certification_count": len(cert_nodes),
            "providers": list(set(
                self.gm.graph.nodes[n].get("category") 
                for n in course_nodes 
                if self.gm.graph.nodes[n].get("category")
            )),
        }


_learning_resource_manager: Optional[LearningResourceManager] = None

def get_learning_resource_manager() -> LearningResourceManager:
    global _learning_resource_manager
    if _learning_resource_manager is None:
        _learning_resource_manager = LearningResourceManager()
    return _learning_resource_manager
