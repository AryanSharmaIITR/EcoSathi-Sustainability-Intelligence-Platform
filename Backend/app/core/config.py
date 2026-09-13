import os
import re
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _to_asyncpg(url: str) -> PostgresDsn:
    """Normalize a Postgres URL to the asyncpg driver scheme SQLAlchemy needs."""
    if url.startswith("postgresql+asyncpg://"):
        return PostgresDsn(url)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    # asyncpg accepts `ssl`, not libpq's `sslmode` query-param name.
    url = re.sub(r"([?&])sslmode=(?P<mode>\w+)", r"\g<1>ssl=\g<mode>", url)
    return PostgresDsn(url)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore", env_ignore_empty=True)

    app_name: str = "EcoSathi"
    api_v1_prefix: str = "/api/v1"
    environment: str = "local"
    app_debug: bool = False

    # Explicit SQLAlchemy URL (postgresql+asyncpg://...). When absent, falls back
    # to the connection strings Vercel creates for its hosted Postgres (Prisma/Neon),
    # which are named after the database.
    database_url: PostgresDsn | None = None
    postgres_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EcoSathiDataBase_POSTGRES_URL", "POSTGRES_URL"),
    )
    prisma_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EcoSathiDataBase_PRISMA_DATABASE_URL", "PRISMA_DATABASE_URL"),
    )

    secret_key: str
    cors_origins: list[str] = ["http://localhost:5173"]

    groq_api_key: str
    groq_vision_model: str = "qwen/qwen3.6-27b"
    groq_orchestration_model: str = "openai/gpt-oss-120b"

    @property
    def effective_database_url(self) -> PostgresDsn:
        if self.database_url is not None:
            return _to_asyncpg(str(self.database_url))
        raw = self.postgres_url or self.prisma_database_url
        if raw is None:
            # Belt-and-suspenders: also scan the raw environment directly, in case
            # the Vercel-hosted Postgres vars don't survive settings loading.
            raw = (
                os.environ.get("EcoSathiDataBase_POSTGRES_URL")
                or os.environ.get("EcoSathiDataBase_PRISMA_DATABASE_URL")
                or os.environ.get("POSTGRES_URL")
                or os.environ.get("PRISMA_DATABASE_URL")
            )
        if raw is None:
            raise RuntimeError(
                "No database URL configured. Set DATABASE_URL (postgresql+asyncpg://...) "
                "or EcoSathiDataBase_POSTGRES_URL."
            )
        return _to_asyncpg(raw)


@lru_cache
def get_settings() -> Settings:
    return Settings()
