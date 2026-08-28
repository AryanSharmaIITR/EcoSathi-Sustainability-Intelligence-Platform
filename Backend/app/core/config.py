from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore", env_ignore_empty=True)

    app_name: str = "EcoSathi"
    api_v1_prefix: str = "/api/v1"
    environment: str = "local"
    app_debug: bool = False
    database_url: PostgresDsn
    secret_key: str
    cors_origins: list[str] = ["http://localhost:5173"]

    groq_api_key: str
    groq_vision_model: str = "qwen/qwen3.6-27b"
    groq_orchestration_model: str = "openai/gpt-oss-120b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
