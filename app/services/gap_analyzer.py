from typing import List, Dict
from app.services.graph_manager import GraphManager
from app.models.user import SkillGap

class GapAnalyzer:
    def __init__(self):
        self.graph_manager = GraphManager()

    def analyze_gaps(self, user_id: str, target_role: str) -> SkillGap:
        required_skills = self.graph_manager.get_role_skills(target_role)
        user_skills = self.graph_manager.get_user_skills(user_id)
        
        gaps = [s for s in required_skills if s not in user_skills]
        matched = [s for s in required_skills if s in user_skills]
        
        gap_courses = {}
        for gap in gaps:
            courses = self.graph_manager.get_courses_for_skill(gap)
            gap_courses[gap] = courses
        
        return SkillGap(
            user_id=user_id,
            target_role=target_role,
            matched_skills=matched,
            missing_skills=gaps,
            courses_for_gaps=gap_courses
        )

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
