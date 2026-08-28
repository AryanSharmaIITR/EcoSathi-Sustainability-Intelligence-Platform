import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.base import APIResponse


class TenantRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool


class TenantCreate(BaseModel):
    name: str
    slug: str
