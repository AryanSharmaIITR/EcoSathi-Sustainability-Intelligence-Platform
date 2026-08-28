import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class AlertIncident(TenantScopedMixin, Base):
    """Generated threshold / anomaly incidents — one row per triggered alert."""

    __tablename__ = "alert_incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # "critical" | "high" | "warning" | "info"
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    # "water_deficit" | "energy_overload" | "roi_negative" | "workforce_deficit"
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)

    metric_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    building: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # "active" | "acknowledged" | "resolved"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
