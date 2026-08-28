import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import APIResponse


class ActionRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    rationale: str
    category: str
    priority: str
    status: str
    progress_pct: int
    estimated_monthly_impact: float | None
    due_date: datetime.date | None
    source: str
    recommended_steps: list[str]
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class ActionUpdate(BaseModel):
    status: Literal["pending", "in_progress", "completed"] | None = None
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class ActionStats(APIResponse):
    total_actions: int
    in_progress_count: int
    pending_count: int
    completed_count: int
    total_actions_wow: int | None = None
    estimated_monthly_impact_total: float


class ActionListResponse(APIResponse):
    stats: ActionStats
    items: list[ActionRead]
    page: int
    page_size: int
    total_items: int
    total_pages: int
