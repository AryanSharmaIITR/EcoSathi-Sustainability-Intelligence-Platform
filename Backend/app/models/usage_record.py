import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class UsageRecord(TenantScopedMixin, Base):
    """One building's water/energy reading for one day. Aggregated by
    app.services.telemetry into the TelemetrySnapshot schema that both the
    /usage dashboard and the resource-planning agent consume."""

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_tenant_resource_date", "tenant_id", "resource_type", "reading_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    building: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "water" | "energy"
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # "L" | "kWh"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DailyWeather(TenantScopedMixin, Base):
    """Tenant-wide weather for one day — not building-specific, used only
    for the Daily Usage Table's temp/rainfall columns (usage-vs-weather
    correlation)."""

    __tablename__ = "daily_weather"
    __table_args__ = (
        Index("ix_daily_weather_tenant_date", "tenant_id", "reading_date", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    avg_temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_mm: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
