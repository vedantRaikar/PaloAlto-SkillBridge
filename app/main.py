import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import get_logger, setup_logging
from app.api.routes import roadmap, user, ingestion, extraction, profile, jobs, courses, chatbot

setup_logging()
logger = get_logger(__name__)

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


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

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


@app.on_event("startup")
async def on_startup():
    logger.info("SkillBridge API starting | version=%s", settings.VERSION)
    from app.services.similarity.semantic_matcher import get_semantic_matcher
    get_semantic_matcher().warmup()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )