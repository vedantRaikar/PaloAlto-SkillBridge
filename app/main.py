from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import roadmap, user, ingestion, extraction, profile, jobs, courses, chatbot

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roadmap.router, prefix=f"{settings.API_V1_STR}/roadmap", tags=["Roadmap"])
app.include_router(user.router, prefix=f"{settings.API_V1_STR}/user", tags=["User"])
app.include_router(ingestion.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingestion"])
app.include_router(extraction.router, prefix=f"{settings.API_V1_STR}/extraction", tags=["Extraction"])
app.include_router(profile.router, prefix=f"{settings.API_V1_STR}/profile", tags=["Profile"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Jobs"])
app.include_router(courses.router, prefix=f"{settings.API_V1_STR}/learning", tags=["Learning Resources"])
app.include_router(chatbot.router, prefix=f"{settings.API_V1_STR}/chatbot", tags=["Chatbot"])

@app.get("/")
async def root():
    return {
        "message": "Skill-Bridge Navigator API",
        "version": settings.VERSION,
        "groq_configured": bool(settings.GROQ_API_KEY)
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "groq_api": "configured" if settings.GROQ_API_KEY else "not_configured"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )