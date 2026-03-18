from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from app.services.profile_builder import ProfileBuilder
from app.models.profile import UserProfile, ProfileMergeRequest
from app.services.graph_manager import GraphManager

router = APIRouter()
profile_builder = ProfileBuilder()
graph_manager = GraphManager()

class GitHubAnalyzeRequest(BaseModel):
    github_username: str

class ManualProfileCreate(BaseModel):
    user_id: str
    name: str
    skills: List[str] = []
    github_username: Optional[str] = None
    email: Optional[str] = None

async def save_profile_background(profile: UserProfile):
    profile_builder.save_to_graph(profile)

@router.post("/github", response_model=UserProfile)
async def analyze_github(req: GitHubAnalyzeRequest, background_tasks: BackgroundTasks):
    profile = await profile_builder.build_from_github_async(req.github_username)
    
    if not profile:
        raise HTTPException(status_code=404, detail="GitHub user not found or API error")
    
    profile_builder.save_to_graph(profile)
    
    return profile

@router.post("/resume", response_model=UserProfile)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    allowed_extensions = ['.pdf', '.docx', '.doc']
    extension = file.filename.lower().split('.')[-1]
    if f'.{extension}' not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {allowed_extensions}"
        )
    
    content = await file.read()
    
    try:
        profile = profile_builder.build_from_resume(
            file_content=content,
            filename=file.filename,
            user_id=user_id
        )
        
        profile_builder.save_to_graph(profile)
        
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")

@router.post("/merge", response_model=UserProfile)
async def merge_profiles(req: ProfileMergeRequest, background_tasks: BackgroundTasks):
    profiles = []
    
    if req.github_username:
        github_profile = await profile_builder.build_from_github_async(req.github_username)
        if github_profile:
            profiles.append(github_profile)
    
    if req.resume_base64 and req.resume_filename:
        try:
            import base64
            content = base64.b64decode(req.resume_base64)
            resume_profile = profile_builder.build_from_resume(
                file_content=content,
                filename=req.resume_filename,
                user_id=req.user_id
            )
            profiles.append(resume_profile)
        except Exception as e:
            pass
    
    if req.additional_skills:
        from app.models.profile import ProfileSource, ContactInfo
        manual_profile = UserProfile(
            id=f"{req.user_id}_manual",
            name="Manual Entry",
            sources=[ProfileSource.MANUAL],
            skills=req.additional_skills,
            contact=ContactInfo()
        )
        profiles.append(manual_profile)
    
    if not profiles:
        raise HTTPException(status_code=400, detail="No profile data provided")
    
    if len(profiles) == 1:
        merged_profile = profiles[0]
    else:
        merged_profile = profile_builder.merge_profiles(profiles)
    
    merged_profile.id = req.user_id
    
    profile_builder.save_to_graph(merged_profile)
    
    return merged_profile

@router.post("/manual", response_model=UserProfile)
async def create_manual_profile(req: ManualProfileCreate):
    github = None
    if req.github_username:
        github = await profile_builder.build_from_github_async(req.github_username)
    
    profile = UserProfile(
        id=req.user_id,
        name=req.name,
        sources=[ProfileSource.MANUAL],
        skills=req.skills,
        github=github,
        contact=ContactInfo(
            email=req.email,
            github=req.github_username
        )
    )
    
    profile_builder.save_to_graph(profile)
    
    return profile

@router.get("/{user_id}", response_model=UserProfile)
async def get_profile(user_id: str):
    node = graph_manager.get_node(user_id)
    
    if not node or node.get('type') != 'user':
        raise HTTPException(status_code=404, detail="Profile not found")
    
    skills = graph_manager.get_user_skills(user_id)
    
    from app.models.profile import ProfileSource, ContactInfo
    
    return UserProfile(
        id=user_id,
        name=node.get('title', 'Unknown'),
        sources=[ProfileSource.MANUAL],
        skills=skills,
        contact=ContactInfo(
            github=node.get('metadata', {}).get('github'),
            email=node.get('metadata', {}).get('email')
        )
    )

@router.get("/{user_id}/readiness")
async def get_readiness_scores(user_id: str, roles: str = ""):
    node = graph_manager.get_node(user_id)
    
    if not node:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    skills = graph_manager.get_user_skills(user_id)
    target_roles = roles.split(",") if roles else [r['id'] for r in graph_manager.get_all_roles()]
    
    profile = UserProfile(
        id=user_id,
        name=node.get('title', 'Unknown'),
        skills=skills
    )
    
    readiness = profile_builder.calculate_readiness(profile, target_roles)
    
    return {
        "user_id": user_id,
        "readiness_scores": readiness
    }

@router.post("/cache/clear")
async def clear_cache():
    profile_builder.clear_github_cache()
    return {"message": "Cache cleared successfully"}

@router.get("/cache/status")
async def cache_status():
    from app.services.github_analyzer import GitHubCache
    return {
        "cached_items": len(GitHubCache._cache),
        "cache_ttl_seconds": 300
    }
