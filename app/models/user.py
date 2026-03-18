from pydantic import BaseModel, Field
from typing import Optional

class UserProfile(BaseModel):
    id: str
    name: str
    skills: list[str] = Field(default_factory=list)
    github_username: Optional[str] = None

class SkillGap(BaseModel):
    user_id: str
    target_role: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    courses_for_gaps: dict[str, list[dict]] = Field(default_factory=dict)

class WeekPlan(BaseModel):
    week: int
    skill: str
    skill_category: Optional[str] = None
    resources: list[dict] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)

class Roadmap(BaseModel):
    user_id: str
    target_role: str
    total_weeks: int
    weeks: list[WeekPlan] = Field(default_factory=list)
    ai_generated: bool = False
    fallback_used: bool = False

class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: Optional[str] = None
    duration_hours: Optional[float] = None
    skills_taught: list[str] = Field(default_factory=list)

class JobDescription(BaseModel):
    title: str
    description: str
    company: Optional[str] = None
    url: Optional[str] = None
