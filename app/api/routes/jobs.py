import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.services.job_ingestion import get_job_ingestion_service
from app.services.extraction_pipeline import ExtractionPipeline
from app.services.graph_manager import GraphManager
from app.models.graph import Node, Link, LinkType
from app.core.config import settings

router = APIRouter()

class JobIngestRequest(BaseModel):
    url: Optional[str] = Field(None, description="LinkedIn job URL")
    text: Optional[str] = Field(None, description="Raw job description text")

class JobData(BaseModel):
    title: str
    company: Optional[str] = None
    description: str
    location: Optional[str] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    industries: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)

class JobResponse(BaseModel):
    job_id: str
    input_type: str
    source: Optional[str] = None
    data: JobData
    extraction_result: Optional[Dict[str, Any]] = None
    graph_updated: bool = False
    role_id: Optional[str] = None
    skills_extracted: int = 0
    timestamp: str

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

@router.post("/ingest", response_model=JobResponse)
async def ingest_job(request: JobIngestRequest):
    if not request.url and not request.text:
        raise HTTPException(
            status_code=400,
            detail="Either 'url' or 'text' must be provided"
        )

    ingestion_service = get_job_ingestion_service()
    
    input_data = request.url or request.text
    result = await ingestion_service.ingest(input_data)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to ingest job")
        suggestion = result.get("suggestion", "")
        
        if suggestion:
            raise HTTPException(
                status_code=422,
                detail=f"{error_msg}. {suggestion}"
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=error_msg
            )

    job_data = result["data"]
    job_id = generate_job_id()
    
    normalized = ingestion_service.normalize_job_for_extraction(job_data)
    
    extraction_result = await process_extraction(
        normalized["title"],
        normalized["description"],
        job_data
    )

    job_record = {
        "job_id": job_id,
        "input_type": result["input_type"],
        "source": result.get("source"),
        "url": result.get("url"),
        "data": job_data,
        "normalized": normalized,
        "extraction_result": extraction_result,
        "graph_updated": extraction_result.get("graph_updated", False),
        "role_id": extraction_result.get("role_id"),
        "skills_extracted": extraction_result.get("skills_extracted", 0),
        "timestamp": datetime.utcnow().isoformat()
    }

    jobs = load_jobs()
    jobs.insert(0, job_record)
    if len(jobs) > 100:
        jobs = jobs[:100]
    save_jobs(jobs)

    return JobResponse(
        job_id=job_id,
        input_type=result["input_type"],
        source=result.get("source"),
        data=JobData(**job_data),
        extraction_result=extraction_result,
        graph_updated=extraction_result.get("graph_updated", False),
        role_id=extraction_result.get("role_id"),
        skills_extracted=extraction_result.get("skills_extracted", 0),
        timestamp=job_record["timestamp"]
    )


async def process_extraction(title: str, description: str, job_data: Dict) -> Dict:
    pipeline = ExtractionPipeline(groq_api_key=os.getenv("GROQ_API_KEY"))
    extraction = await pipeline.extract(title, description)

    extraction_data = extraction.get("extraction_result")
    
    if extraction_data and extraction_data.success and extraction_data.nodes:
        gm = GraphManager()
        
        role_nodes = [n for n in extraction_data.nodes if n.type == "role"]
        skill_nodes = [n for n in extraction_data.nodes if n.type == "skill"]
        
        for node in role_nodes + skill_nodes:
            existing = gm.get_node(node.id)
            if not existing:
                node_data = node.model_dump()
                gm.add_node(Node(**node_data))
        
        role_id = role_nodes[0].id if role_nodes else None
        
        for link in extraction_data.links:
            if not gm.graph.has_edge(link.source, link.target):
                gm.add_edge(link.source, link.target, LinkType.REQUIRES)
        
        if role_id and skill_nodes:
            for skill in skill_nodes:
                if not gm.graph.has_edge(role_id, skill.id):
                    gm.add_edge(role_id, skill.id, LinkType.REQUIRES)
        
        if job_data.get("company"):
            company_id = f"company_{normalize_id(job_data['company'])}"
            if not gm.get_node(company_id):
                gm.add_node(Node(
                    id=company_id,
                    type="company",
                    title=job_data["company"]
                ))
            if role_id and not gm.graph.has_edge(company_id, role_id):
                gm.add_edge(company_id, role_id, LinkType.HIRES)
        
        if job_data.get("location"):
            location_id = f"location_{normalize_id(job_data['location'])}"
            if not gm.get_node(location_id):
                gm.add_node(Node(
                    id=location_id,
                    type="location",
                    title=job_data["location"]
                ))
        
        if job_data.get("experience_level"):
            exp_id = f"exp_{normalize_id(job_data['experience_level'])}"
            if not gm.get_node(exp_id):
                gm.add_node(Node(
                    id=exp_id,
                    type="experience_level",
                    title=job_data["experience_level"]
                ))
            if role_id and not gm.graph.has_edge(role_id, exp_id):
                gm.add_edge(role_id, exp_id, LinkType.REQUIRES)
        
        gm.save_graph()
        
        return {
            "success": True,
            "graph_updated": True,
            "role_id": role_id,
            "skills_extracted": len(skill_nodes),
            "method_used": extraction.get("method_used"),
            "tiers_attempted": extraction.get("tiers_attempted"),
            "fallback_triggered": extraction.get("fallback_triggered", False)
        }
    
    return {
        "success": False,
        "graph_updated": False,
        "skills_extracted": 0,
        "method_used": extraction.get("method_used", "none"),
        "tiers_attempted": extraction.get("tiers_attempted", []),
        "fallback_triggered": extraction.get("fallback_triggered", True)
    }


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


@router.post("/validate")
async def validate_job_input(request: JobIngestRequest):
    ingestion_service = get_job_ingestion_service()
    input_data = request.url or request.text
    
    input_type = ingestion_service.detect_input_type(input_data)
    
    if input_type in ["linkedin_url", "generic_url"]:
        result = await ingestion_service.ingest(input_data)
        if not result.get("success"):
            return {
                "valid": False,
                "error": result.get("error"),
                "input_type": input_type,
                "suggestion": result.get("suggestion")
            }
        return {
            "valid": True,
            "input_type": input_type,
            "preview": {
                "title": result.get("data", {}).get("title"),
                "company": result.get("data", {}).get("company"),
                "description_length": len(result.get("data", {}).get("description", ""))
            }
        }
    
    validation = ingestion_service.validate_job_data({
        "title": input_data.split('\n')[0][:100],
        "description": input_data
    })
    
    return {
        "valid": validation["valid"],
        "input_type": "raw_text",
        "issues": validation["issues"]
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
