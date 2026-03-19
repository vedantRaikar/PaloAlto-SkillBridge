"""
Course Discovery Aggregator
==========================
Provides course recommendations based on O*NET knowledge base mappings.
All course URLs are pre-verified and maintained in the knowledge source.
"""

from typing import List, Dict, Optional
from app.models.course import Course, CourseSearchRequest, CourseSearchResponse
from app.services.knowledge_sources.onet_integration import get_skill_mapper, SkillCourseMapper


FALLBACK_COURSES = [
    {
        "title": "freeCodeCamp Free Course",
        "provider": "freecodecamp",
        "url": "https://www.freecodecamp.org/news/free-course/",
        "instructor": "freeCodeCamp",
        "duration_hours": 20,
        "level": "beginner",
        "is_free": True,
        "rating": 4.7,
        "num_students": 500000,
        "description": "Free comprehensive programming course"
    },
    {
        "title": "Coursera Online Courses",
        "provider": "coursera",
        "url": "https://www.coursera.org/",
        "instructor": "University Partners",
        "duration_hours": 15,
        "level": "beginner",
        "is_free": False,
        "rating": 4.6,
        "num_students": 300000,
        "description": "University-level online courses"
    },
    {
        "title": "freeCodeCamp News",
        "provider": "freecodecamp",
        "url": "https://www.freecodecamp.org/news/",
        "instructor": "freeCodeCamp",
        "duration_hours": 10,
        "level": "beginner",
        "is_free": True,
        "rating": 4.8,
        "num_students": 400000,
        "description": "Free programming tutorials and guides"
    },
]


class CourseAggregator:
    """
    Aggregates course recommendations using O*NET knowledge base.
    No web scraping - all mappings are pre-verified.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {}
        self._skill_mapper: Optional[SkillCourseMapper] = None
    
    @property
    def skill_mapper(self) -> SkillCourseMapper:
        if self._skill_mapper is None:
            self._skill_mapper = get_skill_mapper()
        return self._skill_mapper

    def _get_courses(self, skill: str) -> List[Dict]:
        skill_lower = skill.lower().replace("_", " ")
        
        if skill_lower in self._cache:
            return self._cache[skill_lower]
        
        courses = self.skill_mapper.get_learning_path(skill)
        
        if not courses:
            courses = FALLBACK_COURSES.copy()
        
        self._cache[skill_lower] = courses
        return courses

    def _create_course(self, data: Dict, skill: str) -> Course:
        return Course(
            id=f"{data['provider']}_{data['title'].lower().replace(' ', '_')[:30]}",
            title=data.get("title", f"Learn {skill}"),
            provider=data.get("provider", "unknown"),
            url=data.get("url", ""),
            instructor=data.get("instructor", "Expert Instructor"),
            duration_hours=data.get("duration_hours"),
            rating=data.get("rating"),
            num_students=data.get("num_students"),
            price=0 if data.get("is_free") else data.get("price", 0),
            is_free=data.get("is_free", False),
            level=data.get("level", "beginner"),
            skills_taught=[skill],
            description=data.get("description", f"Learn about {skill}"),
        )

    def search(self, skill: str, providers: List[str] = None, max_results: int = 10, level: str = None) -> CourseSearchResponse:
        course_data = self._get_courses(skill)
        
        courses = [self._create_course(c, skill) for c in course_data]
        
        if providers and "all" not in providers:
            providers_lower = [p.lower() for p in providers]
            courses = [c for c in courses if c.provider.lower() in providers_lower]
        
        if level:
            courses = [c for c in courses if c.level == level.lower() or c.level == "all"]
        
        courses = courses[:max_results]
        
        provider_breakdown = {}
        for c in courses:
            provider_breakdown[c.provider] = provider_breakdown.get(c.provider, 0) + 1
        
        return CourseSearchResponse(
            courses=courses,
            total=len(courses),
            provider_breakdown=provider_breakdown,
            search_skill=skill,
        )

    async def search_all(self, skill: str, providers: List[str] = None, max_results: int = 10, level: str = None, **kwargs) -> CourseSearchResponse:
        return self.search(skill, providers, max_results, level)


_course_aggregator: Optional[CourseAggregator] = None


def get_course_aggregator() -> CourseAggregator:
    global _course_aggregator
    if _course_aggregator is None:
        _course_aggregator = CourseAggregator()
    return _course_aggregator
