import os
import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.services.extraction_pipeline import ExtractionPipeline
from app.services.graph_manager import GraphManager
from app.models.graph import Node, LinkType, NodeType

router = APIRouter()

class RoleBatchIngestRequest(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=120, description="Custom role name")
    job_descriptions: List[str] = Field(..., min_length=2, description="List of similar job descriptions")
    min_frequency: int = Field(1, ge=1, description="Minimum posting count a skill must appear in")


class RoleBatchIngestResponse(BaseModel):
    role_id: str
    role_name: str
    total_postings: int
    valid_postings: int
    skills_extracted_total: int
    skills_selected: int
    selected_skills: List[str]
    skill_frequency: Dict[str, int]
    graph_updated: bool
    readiness_hint: str

JOBS_STORAGE_DIR = Path("data/jobs")
JOBS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def get_jobs_storage_path() -> Path:
    return JOBS_STORAGE_DIR / "jobs.json"

def load_jobs() -> List[Dict]:
    path = get_jobs_storage_path()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def save_jobs(jobs: List[Dict]):
    path = get_jobs_storage_path()
    with open(path, 'w') as f:
        json.dump(jobs, f, indent=2)

def generate_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


@router.post("/ingest-role-batch", response_model=RoleBatchIngestResponse)
async def ingest_role_batch(request: RoleBatchIngestRequest):
    cleaned_descriptions = [d.strip() for d in request.job_descriptions if d and d.strip()]
    if len(cleaned_descriptions) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 non-empty job descriptions are required."
        )

    role_name = request.role_name.strip()
    role_id = normalize_id(role_name)
    if not role_id:
        raise HTTPException(status_code=400, detail="Invalid role_name provided.")

    pipeline = ExtractionPipeline(groq_api_key=os.getenv("GROQ_API_KEY"))
    gm = GraphManager()

    skill_counter: Counter = Counter()
    skill_categories: Dict[str, str] = {}
    valid_postings = 0
    total_extracted = 0

    for description in cleaned_descriptions:
        extraction = await pipeline.extract(role_name, description)
        extraction_result = extraction.get("extraction_result")
        if not extraction_result or not extraction_result.success:
            continue

        posting_skills = set()
        for node in extraction_result.nodes:
            node_type = node.type.value if hasattr(node.type, "value") else str(node.type)
            if node_type != "skill":
                continue
            posting_skills.add(node.id)
            if node.category and node.id not in skill_categories:
                skill_categories[node.id] = node.category

        if posting_skills:
            valid_postings += 1
            total_extracted += len(posting_skills)
            for skill_id in posting_skills:
                skill_counter[skill_id] += 1

    if valid_postings == 0:
        raise HTTPException(
            status_code=422,
            detail="Could not extract skills from the provided job descriptions."
        )

    selected_skills = [
        skill_id
        for skill_id, freq in skill_counter.items()
        if freq >= request.min_frequency
    ]
    selected_skills.sort(key=lambda s: (-skill_counter[s], s))

    if not selected_skills:
        raise HTTPException(
            status_code=422,
            detail="No skills met the selected minimum frequency threshold."
        )

    role_metadata = {
        "source": "synthetic_batch_input",
        "postings_count": len(cleaned_descriptions),
        "valid_postings": valid_postings,
        "min_frequency": request.min_frequency,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if gm.node_exists(role_id):
        for _, target, data in list(gm.graph.out_edges(role_id, data=True)):
            if gm.graph.nodes[target].get("type") == "skill" and data.get("type") == LinkType.REQUIRES.value:
                gm.remove_edge(role_id, target)
        gm.graph.nodes[role_id]["title"] = role_name
        gm.graph.nodes[role_id]["type"] = NodeType.ROLE.value
        gm.graph.nodes[role_id]["metadata"] = role_metadata
    else:
        gm.add_node(Node(
            id=role_id,
            type=NodeType.ROLE,
            title=role_name,
            metadata=role_metadata,
        ))

    for skill_id in selected_skills:
        if not gm.node_exists(skill_id):
            gm.add_node(Node(
                id=skill_id,
                type=NodeType.SKILL,
                title=skill_id.replace("_", " ").title(),
                category=skill_categories.get(skill_id),
                metadata={
                    "source": "synthetic_batch_input"
                }
            ))
        if not gm.graph.has_edge(role_id, skill_id):
            gm.add_edge(role_id, skill_id, LinkType.REQUIRES)

    gm.save_graph()

    jobs = load_jobs()
    jobs.insert(0, {
        "job_id": generate_job_id(),
        "input_type": "role_batch",
        "source": "manual",
        "data": {
            "title": role_name,
            "description": f"Role built from {len(cleaned_descriptions)} job descriptions",
            "skills": selected_skills,
        },
        "normalized": {
            "title": role_name,
            "description": "",
        },
        "extraction_result": {
            "success": True,
            "graph_updated": True,
            "role_id": role_id,
            "skills_extracted": len(selected_skills),
            "method_used": "batch_aggregate",
            "tiers_attempted": ["llm", "dynamic_fallback", "human_loop"],
            "fallback_triggered": False,
        },
        "graph_updated": True,
        "role_id": role_id,
        "skills_extracted": len(selected_skills),
        "timestamp": datetime.utcnow().isoformat(),
    })
    if len(jobs) > 100:
        jobs = jobs[:100]
    save_jobs(jobs)

    return RoleBatchIngestResponse(
        role_id=role_id,
        role_name=role_name,
        total_postings=len(cleaned_descriptions),
        valid_postings=valid_postings,
        skills_extracted_total=total_extracted,
        skills_selected=len(selected_skills),
        selected_skills=selected_skills,
        skill_frequency={k: int(v) for k, v in skill_counter.items()},
        graph_updated=True,
        readiness_hint="Role created. Go to Gap Analysis and select this role to view recommendations."
    )


def normalize_id(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '_', text)
    return text


@router.get("/", response_model=Dict)
async def list_jobs(limit: int = 20, offset: int = 0):
    jobs = load_jobs()
    return {
        "jobs": jobs[offset:offset + limit],
        "total": len(jobs),
        "limit": limit,
        "offset": offset
    }


@router.get("/roles", response_model=Dict)
async def get_discovered_roles():
    gm = GraphManager()
    roles = gm.get_all_roles()
    return {
        "roles": roles,
        "total": len(roles)
    }


@router.get("/skills", response_model=Dict)
async def get_discovered_skills():
    gm = GraphManager()
    skills = gm.get_all_skills()
    return {
        "skills": skills,
        "total": len(skills)
    }


@router.get("/stats")
async def get_job_stats():
    jobs = load_jobs()
    
    companies = set()
    locations = set()
    experience_levels = set()
    total_skills = 0
    methods_used = {}
    
    for job in jobs:
        data = job.get("data", {})
        if data.get("company"):
            companies.add(data["company"])
        if data.get("location"):
            locations.add(data["location"])
        if data.get("experience_level"):
            experience_levels.add(data["experience_level"])
        if data.get("skills"):
            total_skills += len(data["skills"])
        
        extraction = job.get("extraction_result", {})
        method = extraction.get("method_used", "none")
        methods_used[method] = methods_used.get(method, 0) + 1
    
    gm = GraphManager()
    
    return {
        "total_jobs": len(jobs),
        "unique_companies": len(companies),
        "unique_locations": len(locations),
        "unique_experience_levels": len(experience_levels),
        "total_skills_extracted": total_skills,
        "graph_stats": {
            "total_roles": len(gm.get_all_roles()),
            "total_skills": len(gm.get_all_skills()),
            "total_nodes": gm.graph.number_of_nodes(),
            "total_edges": gm.graph.number_of_edges()
        },
        "extraction_methods": methods_used
    }


@router.get("/{job_id}", response_model=Dict)
async def get_job(job_id: str):
    jobs = load_jobs()
    for job in jobs:
        if job["job_id"] == job_id:
            return job
    raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    jobs = load_jobs()
    original_length = len(jobs)
    jobs = [j for j in jobs if j["job_id"] != job_id]

    if len(jobs) == original_length:
        raise HTTPException(status_code=404, detail="Job not found")

    save_jobs(jobs)
    return {"message": f"Job {job_id} deleted", "deleted": True}
