import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.base import APIResponse


class UsageRecordCreate(BaseModel):
    building: str
    resource_type: Literal["water", "energy"]
    reading_date: datetime.date
    value: float
    unit: str
    avg_temp_c: float | None = None
    rainfall_mm: float | None = None


class UsageUploadResponse(APIResponse):
    inserted_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)
