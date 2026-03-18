import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.extraction_pipeline import ExtractionPipeline
from app.services.pending_queue import PendingQueue
from app.services.graph_manager import GraphManager
from app.services.task_queue import task_runner, TaskQueue
from app.models.graph import NodeType, LinkType

router = APIRouter()

class ExtractionRequest(BaseModel):
    title: str
    description: str
    company: Optional[str] = None

class CourseExtractionRequest(BaseModel):
    title: str
    description: str
    provider: str
    url: Optional[str] = None
    duration_hours: Optional[float] = None

class BackgroundTaskResponse(BaseModel):
    task_id: str
    message: str

def normalize_id(name: str) -> str:
    import re
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s]+', '_', name)
    return name

def _process_extraction(req: ExtractionRequest):
    pipeline = ExtractionPipeline(groq_api_key=os.getenv("GROQ_API_KEY"))
    result = pipeline.extract_sync(req.title, req.description)
    
    extraction = result["extraction_result"]
    
    if extraction.success and extraction.nodes:
        gm = GraphManager()
        
        role_nodes = [n for n in extraction.nodes if n.type == "role"]
        skill_nodes = [n for n in extraction.nodes if n.type == "skill"]
        
        for node in role_nodes + skill_nodes:
            existing = gm.get_node(node.id)
            if not existing:
                gm.add_node(node)
        
        for link in extraction.links:
            if not gm.graph.has_edge(link.source, link.target):
                gm.add_edge(link.source, link.target, LinkType.REQUIRES)
        
        gm.save_graph()
        
        return {
            **result,
            "graph_updated": True,
            "role_id": role_nodes[0].id if role_nodes else normalize_id(req.title),
            "skills_added": len(skill_nodes)
        }
    
    return {
        **result,
        "graph_updated": False,
        "message": "Extraction failed - added to pending queue" if result.get("fallback_triggered") else "No skills extracted"
    }

@router.post("/job")
async def extract_job(req: ExtractionRequest):
    return _process_extraction(req)

@router.post("/job/background", response_model=BackgroundTaskResponse)
async def extract_job_background(req: ExtractionRequest, background_tasks: BackgroundTasks):
    task_id = TaskQueue.create_task("job_extraction")
    
    background_tasks.add_task(
        task_runner.run_task_sync,
        task_id,
        lambda: _process_extraction(req)
    )
    
    return BackgroundTaskResponse(
        task_id=task_id,
        message="Job extraction started in background"
    )

@router.get("/job/{task_id}")
async def get_extraction_status(task_id: str):
    task = TaskQueue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@router.post("/course")
async def extract_course(req: CourseExtractionRequest):
    pipeline = ExtractionPipeline(groq_api_key=os.getenv("GROQ_API_KEY"))
    result = pipeline.extract_sync(req.title, req.description)
    
    extraction = result["extraction_result"]
    
    if extraction.success and extraction.nodes:
        gm = GraphManager()
        
        course_id = f"course_{normalize_id(req.title)}"
        
        for skill in extraction.nodes:
            if skill.type == "skill":
                if not gm.get_node(skill.id):
                    gm.add_node(skill)
                if not gm.graph.has_edge(course_id, skill.id):
                    gm.add_edge(course_id, skill.id, LinkType.TEACHES)
        
        gm.save_graph()
        
        return {
            **result,
            "graph_updated": True,
            "course_id": course_id,
            "skills_linked": len([n for n in extraction.nodes if n.type == "skill"])
        }
    
    return {
        **result,
        "graph_updated": False
    }

@router.get("/pending")
async def get_pending_items():
    queue = PendingQueue()
    return {
        "items": queue.get_pending(),
        "stats": queue.get_stats()
    }

@router.post("/pending/{item_id}/retry")
async def retry_pending_item(item_id: str):
    queue = PendingQueue()
    queue.retry(item_id)
    return {"message": f"Item {item_id} queued for retry"}

@router.post("/pending/{item_id}/review")
async def mark_reviewed(item_id: str):
    queue = PendingQueue()
    queue.mark_reviewed(item_id)
    return {"message": f"Item {item_id} marked as reviewed"}

@router.delete("/pending/{item_id}")
async def delete_pending_item(item_id: str):
    queue = PendingQueue()
    queue.remove(item_id)
    return {"message": f"Item {item_id} removed"}

@router.get("/tasks")
async def list_tasks(limit: int = 50):
    return {"tasks": TaskQueue.list_tasks(limit)}
