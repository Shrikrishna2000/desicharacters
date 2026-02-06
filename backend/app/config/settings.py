# backend/app/config/settings.py
from pydantic import Field
from functools import lru_cache
from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # -----------------------------
    # App
    # -----------------------------
    APP_NAME: str = "AI Chat Backend"
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = True
    VERSION: str = "1.0.0"

    # -----------------------------
    # Security
    # -----------------------------
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    # -----------------------------
    # CORS 
    # -----------------------------
    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    # -----------------------------
    # Gemini / LLM Config
    # -----------------------------
    GOOGLE_API_KEY: str = Field(..., env="GOOGLE_API_KEY")
    GOOGLE_MODEL: str = "gemini-2.5-flash"  # default, override if needed

    # -----------------------------
    # Redis
    # -----------------------------
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: str | None = Field(None, env="REDIS_PASSWORD")
    REDIS_POOL_SIZE: int = 20

    # -----------------------------
    # Session Settings
    # -----------------------------
    SESSION_EXPIRATION_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    MAX_TOKENS_PER_SESSION: int = 24000
    MAX_MESSAGES_PER_SESSION: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
