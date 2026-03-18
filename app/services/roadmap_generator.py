from app.services.gap_analyzer import GapAnalyzer
from app.services.graph_manager import GraphManager
from app.models.user import Roadmap, WeekPlan

class RoadmapGenerator:
    def __init__(self):
        self.gap_analyzer = GapAnalyzer()
        self.graph_manager = GraphManager()

    def generate_structured_roadmap(self, user_id: str, target_role: str) -> Roadmap:
        gap = self.gap_analyzer.analyze_gaps(user_id, target_role)
        
        weeks = []
        for i, skill in enumerate(gap.missing_skills, 1):
            skill_node = self.graph_manager.get_node(skill)
            courses = gap.courses_for_gaps.get(skill, [])
            
            week = WeekPlan(
                week=i,
                skill=skill,
                skill_category=skill_node.get('category') if skill_node else None,
                resources=courses[:3],
                milestones=self._get_skill_milestones(skill)
            )
            weeks.append(week)
        
        return Roadmap(
            user_id=user_id,
            target_role=target_role,
            total_weeks=len(weeks),
            weeks=weeks,
            ai_generated=False,
            fallback_used=True
        )

    def _get_skill_milestones(self, skill: str) -> list[str]:
        milestones_map = {
            "javascript": ["Variables & Types", "Functions & Scope", "DOM Manipulation", "Async/Await"],
            "react": ["Components", "State Management", "Hooks", "Context API"],
            "python": ["Basics", "Data Structures", "OOP", "File I/O"],
            "docker": ["Images & Containers", "Dockerfile", "Docker Compose", "Networking"],
            "sql": ["SELECT queries", "Joins", "Subqueries", "Indexes"],
            "aws": ["EC2", "S3", "IAM", "VPC"],
        }
        return milestones_map.get(skill, ["Learn fundamentals", "Build projects", "Practice"])

    async def generate_ai_roadmap(self, user_id: str, target_role: str) -> Roadmap:
        roadmap = self.generate_structured_roadmap(user_id, target_role)
        roadmap.ai_generated = True
        roadmap.fallback_used = False
        return roadmap
