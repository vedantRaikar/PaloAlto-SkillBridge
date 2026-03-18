from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "SkillBridge Navigator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    DATA_DIR: Path = Path("data")
    KNOWLEDGE_GRAPH_PATH: Path = DATA_DIR / "knowledge_graph.json"
    SKILLS_LIBRARY_PATH: Path = DATA_DIR / "skills_library.json"
    PENDING_REVIEW_PATH: Path = DATA_DIR / "pending_review.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
