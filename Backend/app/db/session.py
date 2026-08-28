from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# create_async_engine does not open a connection at import time, so
# importing this module (and hitting /api/v1/health) does not require
# a running Postgres instance.
engine = create_async_engine(str(settings.database_url), echo=settings.app_debug)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
