from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.learning_resource_manager import get_learning_resource_manager
from app.services.course_discovery import get_course_aggregator
from app.services.cert_discovery import get_certification_service

router = APIRouter()

class CourseSearchRequest(BaseModel):
    skill: str = Field(..., description="Skill to search courses for")
    providers: List[str] = Field(default_factory=lambda: ["all"])
    max_results: int = Field(10, ge=1, le=50)
    free_only: bool = Field(False)
    level: Optional[str] = Field(None)
    min_rating: Optional[float] = Field(None, ge=0, le=5)

class CourseDiscoverRequest(BaseModel):
    skills: List[str] = Field(..., description="List of skills to discover courses for")
    budget: str = Field("any", pattern="^(free|paid|any)$")
    max_courses_per_skill: int = Field(5, ge=1, le=20)
    preferred_providers: Optional[List[str]] = Field(None)

class CertificationSearchRequest(BaseModel):
    skill: Optional[str] = Field(None)
    provider: Optional[str] = Field(None)
    level: Optional[str] = Field(None)
    max_results: int = Field(20, ge=1, le=100)

class LearningPathRequest(BaseModel):
    skills: List[str] = Field(..., description="Skills to create learning path for")
    include_certifications: bool = Field(True)
    budget: str = Field("any", pattern="^(free|paid|any)$")


@router.post("/search")
async def search_courses(request: CourseSearchRequest):
    try:
        lrm = get_learning_resource_manager()
        response = await lrm.search_courses(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Course search failed: {str(e)}")


@router.post("/discover")
async def discover_courses(request: CourseDiscoverRequest):
    try:
        lrm = get_learning_resource_manager()
        response = await lrm.discover_courses_for_skills(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Course discovery failed: {str(e)}")


@router.get("/for-skill/{skill_id}")
async def get_courses_for_skill(skill_id: str):
    try:
        lrm = get_learning_resource_manager()
        resources = lrm.get_learning_resources_for_skill(skill_id)
        return resources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get courses: {str(e)}")


@router.get("/providers")
async def get_course_providers():
    aggregator = get_course_aggregator()
    providers = list(aggregator.scrapers.keys())
    return {
        "providers": providers,
        "total": len(providers)
    }


@router.get("/stats")
async def get_course_stats():
    try:
        lrm = get_learning_resource_manager()
        stats = lrm.get_graph_stats()
        return {
            "course_stats": {
                "cached_courses": len(lrm.cached_courses) if lrm.cached_courses else 0,
                "providers_active": len(lrm.course_aggregator.scrapers)
            },
            "graph_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certifications/search")
async def search_certifications(
    skill: Optional[str] = None,
    provider: Optional[str] = None,
    level: Optional[str] = None,
    max_results: int = 20
):
    try:
        lrm = get_learning_resource_manager()
        response = lrm.search_certifications(
            skill=skill,
            provider=provider,
            level=level,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Certification search failed: {str(e)}")


@router.get("/certifications/providers")
async def get_certification_providers():
    try:
        cert_service = get_certification_service()
        providers = cert_service.get_providers()
        return {
            "providers": [p.model_dump() for p in providers],
            "total": len(providers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certifications/{cert_id}")
async def get_certification(cert_id: str):
    try:
        cert_service = get_certification_service()
        cert = cert_service.get_by_id(cert_id)
        if not cert:
            raise HTTPException(status_code=404, detail="Certification not found")
        
        career_path = cert_service.get_career_path(cert_id)
        prereqs = cert_service.get_prerequisites(cert_id)
        
        return {
            "certification": cert.model_dump(),
            "career_path": [c.model_dump() for c in career_path],
            "prerequisites": [p.model_dump() for p in prereqs],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certifications/recommend")
async def recommend_certifications(skills: List[str]):
    try:
        lrm = get_learning_resource_manager()
        recommendations = lrm.recommend_certifications_for_skills(skills)
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-paths")
async def generate_learning_paths(request: LearningPathRequest):
    try:
        lrm = get_learning_resource_manager()
        
        cert_recommendations = []
        if request.include_certifications:
            cert_recommendations = lrm.recommend_certifications_for_skills(request.skills)
        
        courses_by_skill = {}
        for skill in request.skills:
            try:
                from app.models.course import CourseSearchRequest as CSRequest
                search_req = CSRequest(
                    skill=skill,
                    max_results=5,
                    free_only=request.budget == "free"
                )
                response = await lrm.search_courses(search_req)
                courses_by_skill[skill] = response.courses
            except Exception:
                courses_by_skill[skill] = []
        
        return {
            "skills": request.skills,
            "courses_by_skill": {k: [c.model_dump() for c in v] for k, v in courses_by_skill.items()},
            "certification_recommendations": cert_recommendations[:5],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/for-gap-analysis")
async def get_resources_for_gap(
    missing_skills: str = "",
    matched_skills: str = ""
):
    try:
        missing = missing_skills.split(",") if missing_skills else []
        matched = matched_skills.split(",") if matched_skills else []
        
        lrm = get_learning_resource_manager()
        
        resources = {}
        for skill in missing:
            if skill:
                resources[skill] = lrm.get_learning_resources_for_skill(skill.strip())
        
        return {
            "missing_skills": missing,
            "matched_skills": matched,
            "resources": resources,
            "summary": {
                "total_missing_skills": len(missing),
                "skills_with_courses": len([s for s in missing if resources.get(s, {}).get("courses", [])]),
                "skills_with_certs": len([s for s in missing if resources.get(s, {}).get("certifications", [])]),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
