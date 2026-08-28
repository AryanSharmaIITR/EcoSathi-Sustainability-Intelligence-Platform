import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.base import AIGeneratedResponse


class ActionItem(BaseModel):
    title: str
    priority: Literal["high", "medium", "low"]
    rationale: str
    category: Literal["water", "energy", "waste", "general"] = "general"
    estimated_monthly_impact: float | None = None


class ActionItemWithId(ActionItem):
    """ActionItem enriched with the persisted DB row id, returned by
    POST /api/v1/recommend so the frontend can selectively delete rows."""
    id: uuid.UUID


class RecommendationResponse(AIGeneratedResponse):
    actions: list[ActionItemWithId]
