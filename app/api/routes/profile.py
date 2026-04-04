from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import csv
from pathlib import Path
from datetime import datetime
from app.services.profile_builder import ProfileBuilder
from app.models.profile import UserProfile, ProfileMergeRequest, ProfileSource, ContactInfo
from app.services.graph_manager import GraphManager
from app.models.graph import Node, NodeType, LinkType
from app.core.config import settings

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


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    skills: Optional[List[str]] = None
    github_username: Optional[str] = None
    email: Optional[str] = None
    refresh_resources: bool = False


CSV_HEADERS = [
    "user_id",
    "name",
    "email",
    "github_username",
    "skills",
    "sources",
    "experience_years",
    "updated_at",
]


def _get_profiles_csv_path() -> Path:
    return settings.DATA_DIR / "profiles.csv"


def _upsert_profile_csv(profile: UserProfile):
    path = _get_profiles_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = {}
    if path.exists():
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get("user_id")
                if uid:
                    rows[uid] = row

    rows[profile.id] = {
        "user_id": profile.id,
        "name": profile.name,
        "email": profile.contact.email or "",
        "github_username": profile.contact.github or "",
        "skills": ",".join(profile.skills),
        "sources": ",".join([s.value for s in profile.sources]),
        "experience_years": "" if profile.experience_years is None else str(profile.experience_years),
        "updated_at": datetime.utcnow().isoformat(),
    }

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for uid in sorted(rows.keys()):
            writer.writerow(rows[uid])

async def save_profile_background(profile: UserProfile):
    profile_builder.save_to_graph(profile)

@router.post("/github", response_model=UserProfile)
async def analyze_github(req: GitHubAnalyzeRequest, background_tasks: BackgroundTasks):
    profile = await profile_builder.build_from_github_async(req.github_username)
    
    if not profile:
        raise HTTPException(status_code=404, detail="GitHub user not found or API error")
    
    profile_builder.save_to_graph(profile)
    _upsert_profile_csv(profile)
    
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
        _upsert_profile_csv(profile)
        
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
    _upsert_profile_csv(merged_profile)
    
    return merged_profile

@router.post("/manual", response_model=UserProfile)
async def create_manual_profile(req: ManualProfileCreate):
    github_profile = None
    if req.github_username:
        github_user_profile = await profile_builder.build_from_github_async(req.github_username)
        if github_user_profile:
            github_profile = github_user_profile.github
    
    profile = UserProfile(
        id=req.user_id,
        name=req.name,
        sources=[ProfileSource.MANUAL],
        skills=req.skills,
        github=github_profile,
        contact=ContactInfo(
            email=req.email,
            github=req.github_username
        )
    )
    
    profile_builder.save_to_graph(profile)
    _upsert_profile_csv(profile)
    
    return profile


@router.patch("/{user_id}", response_model=UserProfile)
async def update_profile(user_id: str, req: ProfileUpdateRequest):
    node = graph_manager.get_node(user_id)
    if not node or node.get('type') != 'user':
        raise HTTPException(status_code=404, detail="Profile not found")

    if (
        req.name is None
        and req.skills is None
        and req.github_username is None
        and req.email is None
    ):
        raise HTTPException(status_code=400, detail="No fields provided for update")

    if req.name is not None:
        name = req.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        graph_manager.graph.nodes[user_id]['title'] = name

    metadata = dict(graph_manager.graph.nodes[user_id].get('metadata', {}))
    if req.github_username is not None:
        metadata['github'] = req.github_username.strip() if req.github_username else None
    if req.email is not None:
        metadata['email'] = req.email.strip() if req.email else None
    graph_manager.graph.nodes[user_id]['metadata'] = metadata

    if req.skills is not None:
        # Replace user skill edges to make updates explicit and deterministic.
        existing_edges = []
        for source, target in graph_manager.graph.out_edges(user_id):
            if graph_manager.graph.nodes[target].get('type') == 'skill':
                existing_edges.append((source, target))
        for source, target in existing_edges:
            graph_manager.remove_edge(source, target)

        normalized_skills: List[str] = []
        seen = set()
        for skill in req.skills:
            skill_id = (skill or "").strip().lower().replace(" ", "_")
            if not skill_id or skill_id in seen:
                continue
            seen.add(skill_id)
            normalized_skills.append(skill_id)

        for skill_id in normalized_skills:
            graph_manager.add_user_skill(
                user_id,
                skill_id,
                category='programming',
                metadata={'source': 'manual_profile_update'},
                enrich_resources=True,
                force_refresh=req.refresh_resources,
            )

    graph_manager.save_graph()
    updated_profile = await get_profile(user_id)
    _upsert_profile_csv(updated_profile)
    return updated_profile


@router.get("/{user_id}/graph")
async def get_user_knowledge_graph(user_id: str, depth: int = 2):
    node = graph_manager.get_node(user_id)
    if not node or node.get('type') != 'user':
        raise HTTPException(status_code=404, detail="Profile not found")

    max_depth = 3
    if depth < 1 or depth > max_depth:
        raise HTTPException(status_code=400, detail=f"depth must be between 1 and {max_depth}")

    visited = {user_id}
    frontier = {user_id}

    for _ in range(depth):
        next_frontier = set()
        for current in frontier:
            if current not in graph_manager.graph:
                continue

            for neighbor in graph_manager.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)

            for neighbor in graph_manager.graph.predecessors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)

        frontier = next_frontier
        if not frontier:
            break

    nodes = []
    for node_id in visited:
        nodes.append({
            "id": node_id,
            **graph_manager.graph.nodes[node_id],
        })

    edges = []
    for source, target, data in graph_manager.graph.edges(data=True):
        if source in visited and target in visited:
            edges.append({
                "source": source,
                "target": target,
                **data,
            })

    return {
        "user_id": user_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }

@router.get("/{user_id}", response_model=UserProfile)
async def get_profile(user_id: str):
    node = graph_manager.get_node(user_id)
    
    if not node or node.get('type') != 'user':
        raise HTTPException(status_code=404, detail="Profile not found")
    
    skills = graph_manager.get_user_skills(user_id)
    
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
