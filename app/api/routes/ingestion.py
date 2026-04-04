from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.graph_manager import GraphManager
from app.models.graph import Node, Link, LinkType, NodeType
from typing import List, Optional

router = APIRouter()
graph_manager = GraphManager()

class JobIngest(BaseModel):
    title: str
    description: str
    company: Optional[str] = None
    skills: List[str] = []
    url: Optional[str] = None

class CourseIngest(BaseModel):
    title: str
    provider: str
    url: Optional[str] = None
    duration_hours: Optional[float] = None
    skills_taught: List[str] = []

class SkillAdd(BaseModel):
    id: str
    category: Optional[str] = None
    aliases: List[str] = []

def normalize_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")

@router.post("/job")
async def ingest_job(job: JobIngest):
    role_id = normalize_id(job.title)
    
    role_node = Node(
        id=role_id,
        type=NodeType.ROLE,
        title=job.title,
        metadata={"company": job.company, "url": job.url}
    )
    graph_manager.add_node(role_node)
    
    for skill in job.skills:
        skill_id = normalize_id(skill)
        graph_manager.ensure_skill_node(
            skill_id,
            category="ingested",
            title=skill.replace("_", " ").title(),
            metadata={"source": "job_ingestion"},
            enrich_resources=True,
        )
        graph_manager.add_edge(role_id, skill_id, LinkType.REQUIRES)
    
    graph_manager.save_graph()
    return {"message": "Job ingested", "role_id": role_id, "skills_count": len(job.skills)}

@router.post("/course")
async def ingest_course(course: CourseIngest):
    course_id = f"course_{normalize_id(course.title)}"
    
    course_node = Node(
        id=course_id,
        type=NodeType.COURSE,
        title=course.title,
        metadata={
            "provider": course.provider,
            "url": course.url,
            "duration_hours": course.duration_hours
        }
    )
    graph_manager.add_node(course_node)
    
    for skill in course.skills_taught:
        skill_id = normalize_id(skill)
        graph_manager.ensure_skill_node(
            skill_id,
            category="ingested",
            title=skill.replace("_", " ").title(),
            metadata={"source": "course_ingestion"},
            enrich_resources=True,
        )
        graph_manager.add_edge(course_id, skill_id, LinkType.TEACHES)
    
    graph_manager.save_graph()
    return {"message": "Course ingested", "course_id": course_id}

@router.post("/skill")
async def add_skill(skill: SkillAdd):
    skill_id = normalize_id(skill.id)

    graph_manager.ensure_skill_node(
        skill_id,
        category=skill.category or "programming",
        title=skill.id.replace("_", " ").title(),
        metadata={"source": "manual_skill_add", "aliases": skill.aliases},
        enrich_resources=True,
    )
    graph_manager.save_graph()
    
    return {"message": "Skill added", "skill_id": skill_id}

@router.post("/link")
async def add_link(source: str, target: str, link_type: LinkType):
    source_id = normalize_id(source)
    target_id = normalize_id(target)
    
    if not graph_manager.get_node(source_id):
        raise HTTPException(status_code=404, detail=f"Source node '{source_id}' not found")
    if not graph_manager.get_node(target_id):
        raise HTTPException(status_code=404, detail=f"Target node '{target_id}' not found")
    
    graph_manager.add_edge(source_id, target_id, link_type)
    graph_manager.save_graph()
    
    return {"message": "Link added", "source": source_id, "target": target_id, "type": link_type.value}
