from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )
    
    PROJECT_NAME: str = "SkillBridge Navigator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    DATA_DIR: Path = Path("data")
    KNOWLEDGE_GRAPH_PATH: Path = DATA_DIR / "knowledge_graph.json"
    SKILLS_LIBRARY_PATH: Path = DATA_DIR / "skills_library.json"
    PENDING_REVIEW_PATH: Path = DATA_DIR / "pending_review.json"
    
    GROQ_API_KEY: str = ""
    GITHUB_TOKEN: str = ""

settings = Settings()
