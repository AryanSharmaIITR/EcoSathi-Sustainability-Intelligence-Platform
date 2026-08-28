import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import APIResponse


class AlertIncidentRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    severity: str
    trigger_type: str
    title: str
    message: str
    metric_actual: float | None = None
    metric_limit: float | None = None
    metric_unit: str | None = None
    building: str | None = None
    ai_recommendation: str | None = None
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class AlertIncidentUpdate(BaseModel):
    # Only status transitions are allowed from the API
    status: str  # "acknowledged" | "resolved"


class AlertStats(APIResponse):
    total_active: int
    critical_count: int
    high_count: int
    warning_count: int
    info_count: int


class AlertsListResponse(APIResponse):
    stats: AlertStats
    items: list[AlertIncidentRead]
