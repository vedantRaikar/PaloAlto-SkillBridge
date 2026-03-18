from fastapi import APIRouter, HTTPException
from app.services.gap_analyzer import GapAnalyzer
from app.services.roadmap_generator import RoadmapGenerator
from app.services.graph_manager import GraphManager

router = APIRouter()
gap_analyzer = GapAnalyzer()
roadmap_generator = RoadmapGenerator()
graph_manager = GraphManager()

@router.get("/roles")
async def get_available_roles():
    roles = graph_manager.get_all_roles()
    return {"roles": roles}

@router.get("/skills")
async def get_available_skills():
    skills = graph_manager.get_all_skills()
    return {"skills": skills}

@router.get("/{user_id}/{target_role}/gap-analysis")
async def analyze_gap(user_id: str, target_role: str):
    gap = gap_analyzer.analyze_gaps(user_id, target_role)
    readiness = gap_analyzer.calculate_readiness_score(user_id, target_role)
    return {
        "gap_analysis": gap,
        "readiness_score": readiness
    }

@router.get("/{user_id}/{target_role}/roadmap")
async def get_roadmap(user_id: str, target_role: str):
    roadmap = roadmap_generator.generate_structured_roadmap(user_id, target_role)
    return roadmap

@router.get("/{user_id}/{target_role}/requirements")
async def get_role_requirements(user_id: str, target_role: str):
    requirements = gap_analyzer.get_role_requirements(target_role)
    readiness = gap_analyzer.calculate_readiness_score(user_id, target_role)
    return {
        **requirements,
        "user_readiness_score": readiness
    }
