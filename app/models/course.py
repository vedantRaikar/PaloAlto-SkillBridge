from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"

class CourseProvider(str, Enum):
    UDEMY = "udemy"
    COURSERA = "coursera"
    EDX = "edx"
    YOUTUBE = "youtube"
    PLURALSIGHT = "pluralsight"
    UDACITY = "udacity"
    LINKEDIN_LEARNING = "linkedin_learning"
    OTHER = "other"

class Course(BaseModel):
    id: str = Field(..., description="Unique course identifier with provider prefix")
    title: str = Field(..., description="Course title")
    provider: str = Field(..., description="Course provider platform")
    url: str = Field(..., description="Course URL")
    instructor: Optional[str] = Field(None, description="Instructor name")
    duration_hours: Optional[float] = Field(None, description="Course duration in hours")
    rating: Optional[float] = Field(None, description="Course rating (0-5)")
    num_ratings: Optional[int] = Field(None, description="Number of ratings")
    num_students: Optional[int] = Field(None, description="Number of enrolled students")
    price: Optional[float] = Field(None, description="Course price in USD")
    is_free: bool = Field(False, description="Whether the course is free")
    level: str = Field("all_levels", description="Course difficulty level")
    skills_taught: List[str] = Field(default_factory=list, description="List of skill IDs taught")
    thumbnail_url: Optional[str] = Field(None, description="Course thumbnail URL")
    description: Optional[str] = Field(None, description="Course description")
    curriculum_summary: Optional[str] = Field(None, description="Brief curriculum summary")
    language: Optional[str] = Field("en", description="Course language")
    last_updated: Optional[str] = Field(None, description="Last update date")
    source: str = Field("scraped", description="Data source (scraped, api, manual)")
    relevance_score: Optional[float] = Field(None, description="Relevance score for the search query")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_graph_node(self) -> dict:
        return {
            "id": f"course_{self.id}",
            "type": "course",
            "title": self.title,
            "provider": self.provider,
            "url": self.url,
            "instructor": self.instructor,
            "duration_hours": self.duration_hours,
            "rating": self.rating,
            "num_students": self.num_students,
            "price": self.price if not self.is_free else 0,
            "is_free": self.is_free,
            "level": self.level,
            "thumbnail_url": self.thumbnail_url,
        }


class CourseSearchRequest(BaseModel):
    skill: str = Field(..., description="Skill to search courses for")
    providers: List[str] = Field(default_factory=lambda: ["all"], description="Provider filters")
    max_results: int = Field(10, ge=1, le=50, description="Maximum results per provider")
    free_only: bool = Field(False, description="Filter for free courses only")
    level: Optional[str] = Field(None, description="Filter by course level")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating filter")


class CourseSearchResponse(BaseModel):
    courses: List[Course] = Field(default_factory=list)
    total: int = Field(0, description="Total courses found")
    provider_breakdown: dict = Field(default_factory=dict, description="Courses per provider")
    search_skill: str = Field(..., description="Original search query")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CourseDiscoverRequest(BaseModel):
    skills: List[str] = Field(..., description="List of skills to discover courses for")
    budget: str = Field("any", description="Budget: free, paid, or any")
    max_courses_per_skill: int = Field(5, ge=1, le=20)
    preferred_providers: Optional[List[str]] = Field(None)


class CourseDiscoverResponse(BaseModel):
    courses_by_skill: dict = Field(default_factory=dict, description="Courses grouped by skill")
    recommended_paths: List[dict] = Field(default_factory=list, description="Suggested learning paths")
    total_courses: int = Field(0)


class CourseRefreshRequest(BaseModel):
    skill: Optional[str] = Field(None, description="Refresh courses for specific skill")
    provider: Optional[str] = Field(None, description="Refresh from specific provider")
    force: bool = Field(False, description="Force refresh even if cached")


class CourseStorage(BaseModel):
    courses: List[Course] = Field(default_factory=list)
    last_refresh: Optional[str] = Field(None)
    total_cached: int = Field(0)
