from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.graph_manager import GraphManager
from app.models.graph import Node, LinkType, NodeType
from typing import List

router = APIRouter()
graph_manager = GraphManager()

class UserCreate(BaseModel):
    id: str
    name: str
    skills: List[str] = []

class UserSkillsUpdate(BaseModel):
    skills: List[str]

@router.post("/")
async def create_user(user: UserCreate):
    user_node = Node(
        id=user.id,
        type=NodeType.USER,
        title=user.name,
        metadata={"github": None}
    )
    graph_manager.add_node(user_node)
    
    for skill in user.skills:
        graph_manager.add_user_skill(
            user.id,
            skill,
            category="programming",
            metadata={"source": "user_create"},
            enrich_resources=True,
        )
    
    graph_manager.save_graph()
    return {"message": "User created", "user_id": user.id}

@router.get("/{user_id}/skills")
async def get_user_skills(user_id: str):
    skills = graph_manager.get_user_skills(user_id)
    return {"user_id": user_id, "skills": skills}

@router.put("/{user_id}/skills")
async def update_user_skills(user_id: str, update: UserSkillsUpdate):
    for skill in update.skills:
        graph_manager.add_user_skill(
            user_id,
            skill,
            category="programming",
            metadata={"source": "user_skill_update"},
            enrich_resources=True,
        )
    
    graph_manager.save_graph()
    return {"message": "Skills updated", "user_id": user_id, "skills": update.skills}

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    if user_id in graph_manager.graph:
        graph_manager.graph.remove_node(user_id)
        graph_manager.save_graph()
        return {"message": "User deleted"}
    raise HTTPException(status_code=404, detail="User not found")
