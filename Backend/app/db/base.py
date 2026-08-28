from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models. Imported by Alembic's
    env.py for autogenerate once migrations are scaffolded."""
