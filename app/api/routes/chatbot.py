from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.services.chatbot.graph_rag_chatbot import get_graph_rag_chatbot

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []
    selected_role: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    context_used: bool
    intent: str
    suggestions: List[str]
    entities_found: Dict[str, List[str]]


class SuggestionsResponse(BaseModel):
    suggestions: List[str]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask the Graph RAG chatbot a question about skills, careers, or learning resources.
    """
    try:
        chatbot = get_graph_rag_chatbot()
        
        history = []
        for msg in request.history:
            history.append({
                "role": msg.role,
                "user": msg.content if msg.role == "user" else "",
                "assistant": msg.content if msg.role == "assistant" else ""
            })
        
        result = chatbot.ask(request.question, history, request.selected_role)
        
        return ChatResponse(
            answer=result["answer"],
            context_used=result["context_used"],
            intent=result["intent"],
            suggestions=result["suggestions"],
            entities_found=result["entities_found"],
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions():
    """
    Get initial conversation starters for the chatbot.
    """
    try:
        chatbot = get_graph_rag_chatbot()
        suggestions = chatbot._get_suggestions()
        return SuggestionsResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def get_capabilities():
    """
    Get information about what the chatbot can help with.
    """
    return {
        "capabilities": [
            {
                "category": "Career Guidance",
                "examples": [
                    "What skills do I need to become a data scientist?",
                    "How can I transition from frontend to full-stack?",
                    "What's the best path to become a DevOps engineer?"
                ]
            },
            {
                "category": "Learning Resources",
                "examples": [
                    "Where can I learn Python?",
                    "Recommend courses for AWS certification",
                    "Best free resources to learn Kubernetes"
                ]
            },
            {
                "category": "Skill Comparison",
                "examples": [
                    "React vs Angular - which should I learn?",
                    "Difference between AWS and Azure",
                    "Should I learn Go or Rust?"
                ]
            },
            {
                "category": "Certification Advice",
                "examples": [
                    "Which AWS certification should I start with?",
                    "Best certifications for cloud careers",
                    "How to prepare for the Azure Administrator exam"
                ]
            },
            {
                "category": "Skill Gap Analysis",
                "examples": [
                    "What skills am I missing for a backend role?",
                    "How long to become job-ready in data science?",
                    "Essential skills for a frontend developer"
                ]
            }
        ],
        "knowledge_sources": [
            "O*NET occupation database",
            "Skill taxonomy and relationships",
            "Course and certification catalog",
            "Technology compatibility mapping"
        ]
    }
