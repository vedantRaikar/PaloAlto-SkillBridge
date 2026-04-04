import os
from math import ceil
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.services.gap_analyzer import GapAnalyzer
from app.services.graph_manager import GraphManager
from app.models.user import Roadmap, WeekPlan
from app.core.config import settings
from app.services.fast_track_generator import get_fast_track_generator

MILESTONES_PROMPT = PromptTemplate.from_template('''
For each skill listed, suggest appropriate learning milestones/progression steps.

Return ONLY valid JSON:
{{
  "milestones": {{
    "skill_name": ["Step 1", "Step 2", "Step 3", "Step 4"]
  }}
}}

Skills to create milestones for: {skills}

JSON Response:
''')

ROADMAP_PROMPT = PromptTemplate.from_template('''
Based on the user's current skills and target role, create a structured learning roadmap.

User's current skills: {current_skills}
Target role: {target_role}
Skills to learn: {missing_skills}

Return ONLY valid JSON:
{{
  "weeks": [
    {{
      "skill": "skill_name",
      "skill_category": "category",
      "milestones": ["Milestone 1", "Milestone 2", "Milestone 3"],
      "estimated_days": 7
    }}
  ],
  "total_weeks": 12,
  "learning_order_rationale": "Brief explanation of why skills are ordered this way"
}}

JSON Response:
''')


class RoadmapGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.gap_analyzer = GapAnalyzer()
        self.graph_manager = GraphManager()
        self.api_key = api_key or settings.GROQ_API_KEY
        self._llm = None
        self._milestones_cache: dict = {}

    def _initialize_llm(self):
        if self._llm is None and self.api_key:
            self._llm = ChatGroq(
                api_key=self.api_key,
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=2048
            )

    async def _generate_milestones_llm(self, skills: List[str]) -> dict:
        if not skills:
            return {}
        
        cache_key = ','.join(sorted(skills))
        if cache_key in self._milestones_cache:
            return self._milestones_cache[cache_key]
        
        self._initialize_llm()
        if not self._llm:
            return {s: ["Learn fundamentals", "Build projects", "Practice"] for s in skills}
        
        try:
            from pydantic import BaseModel, Field
            class MilestoneItem(BaseModel):
                skill: str
                milestones: List[str] = Field(default_factory=list)
            
            class MilestonesOutput(BaseModel):
                milestones: dict = Field(default_factory=dict)
            
            chain = MILESTONES_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({"skills": ', '.join(skills)})
            
            milestones = result.get("milestones", {})
            self._milestones_cache[cache_key] = milestones
            return milestones
        except Exception:
            return {s: ["Learn fundamentals", "Build projects", "Practice"] for s in skills}

    async def _generate_roadmap_llm(self, current_skills: List[str], target_role: str, missing_skills: List[str]) -> dict:
        self._initialize_llm()
        if not self._llm:
            return None
        
        try:
            chain = ROADMAP_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({
                "current_skills": ', '.join(current_skills),
                "target_role": target_role,
                "missing_skills": ', '.join(missing_skills)
            })
            return result
        except Exception:
            return None

    def generate_structured_roadmap(self, user_id: str, target_role: str) -> Roadmap:
        gap = self.gap_analyzer.analyze_gaps(user_id, target_role)
        fast_track = get_fast_track_generator()
        
        weeks = []
        current_week = 1
        for skill in gap.missing_skills:
            skill_node = self.graph_manager.get_node(skill)
            courses = gap.courses_for_gaps.get(skill, [])
            skill_weeks = max(1, ceil(fast_track.estimate_total_weeks_for_skills([skill], target_role)))
            
            week = WeekPlan(
                week=current_week,
                skill=skill,
                skill_category=skill_node.get('category') if skill_node else None,
                resources=courses[:3],
                milestones=["Learn fundamentals", "Build projects", "Practice"]
            )
            weeks.append(week)
            current_week += skill_weeks
        
        total_weeks = int(max(0, current_week - 1))
        
        return Roadmap(
            user_id=user_id,
            target_role=target_role,
            total_weeks=total_weeks,
            weeks=weeks,
            ai_generated=False,
            fallback_used=True
        )

    def _get_skill_milestones(self, skill: str) -> list[str]:
        if skill in self._milestones_cache:
            return self._milestones_cache[skill]
        return ["Learn fundamentals", "Build projects", "Practice"]

    async def generate_ai_roadmap(self, user_id: str, target_role: str) -> Roadmap:
        gap = self.gap_analyzer.analyze_gaps(user_id, target_role)
        fast_track = get_fast_track_generator()
        
        llm_roadmap = await self._generate_roadmap_llm(
            gap.user_skills,
            target_role,
            gap.missing_skills
        )
        
        if llm_roadmap:
            milestones_map = await self._generate_milestones_llm(gap.missing_skills)
            
            weeks = []
            current_week = 1
            for week_data in llm_roadmap.get("weeks", []):
                skill = week_data.get("skill", "")
                skill_node = self.graph_manager.get_node(skill)
                courses = gap.courses_for_gaps.get(skill, [])
                skill_weeks = max(1, ceil(fast_track.estimate_total_weeks_for_skills([skill], target_role)))
                
                week = WeekPlan(
                    week=current_week,
                    skill=skill,
                    skill_category=week_data.get("skill_category") or skill_node.get('category') if skill_node else None,
                    resources=courses[:3],
                    milestones=week_data.get("milestones", milestones_map.get(skill, ["Learn fundamentals", "Build projects", "Practice"]))
                )
                weeks.append(week)
                current_week += skill_weeks
            
            total_weeks = int(max(0, current_week - 1))
            
            return Roadmap(
                user_id=user_id,
                target_role=target_role,
                total_weeks=total_weeks,
                weeks=weeks,
                ai_generated=True,
                fallback_used=False
            )
        
        return self.generate_structured_roadmap(user_id, target_role)


_roadmap_generator = None

def get_roadmap_generator(api_key: Optional[str] = None) -> RoadmapGenerator:
    global _roadmap_generator
    if _roadmap_generator is None:
        _roadmap_generator = RoadmapGenerator(api_key=api_key)
    return _roadmap_generator
