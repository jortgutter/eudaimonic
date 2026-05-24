"""Application configuration"""
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App
    APP_NAME: str = "Movie Recommendation API"
    APP_VERSION: str = "0.0.1"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    SQLALCHEMY_DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
        validation_alias="DATABASE_URL",
    )
    MOVIES_DB_PATH: str = Field(
        default_factory=lambda: os.getenv("MOVIES_DB_PATH", "./app/database/movies.db"),
        validation_alias="MOVIES_DB_PATH",
    )
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "your-secret-key-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LLM (Open WebUI/OpenAI-compatible)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_CHAT_PATH: str = os.getenv("LLM_CHAT_PATH", "/api/chat/completions")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    # TMDb
    TMDB_BASE_URL: str = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_IMAGE_BASE_URL: str = os.getenv(
        "TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500"
    )
    TMDB_TIMEOUT_SECONDS: int = int(os.getenv("TMDB_TIMEOUT_SECONDS", "30"))
    
    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://145.116.129.10:8081",
    ]
    ALLOWED_ORIGIN_REGEX: str = r"https?://.*" if os.getenv("DEBUG", "False").lower() == "true" else r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
