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

@router.get("/graph")
async def get_graph_data(
    type: str | None = None,
    category: str | None = None,
    limit: int = 100
):
    nodes = []
    edges = []
    
    all_nodes = list(graph_manager.graph.nodes())
    filtered_nodes = all_nodes
    
    if type:
        filtered_nodes = [n for n in all_nodes if graph_manager.graph.nodes[n].get('type') == type]
    
    for node_id in filtered_nodes[:limit]:
        node_data = graph_manager.graph.nodes[node_id]
        nodes.append({
            "id": node_id,
            "type": node_data.get("type"),
            "title": node_data.get("title", node_id),
            "category": node_data.get("category"),
            "metadata": node_data.get("metadata", {}),
        })
        
        for target in graph_manager.graph.successors(node_id):
            edge_data = graph_manager.graph.edges[node_id, target]
            edges.append({
                "source": node_id,
                "target": target,
                "type": edge_data.get("type"),
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": graph_manager.get_graph_stats()
    }

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
