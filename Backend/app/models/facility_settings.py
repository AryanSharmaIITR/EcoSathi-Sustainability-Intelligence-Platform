import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class FacilitySettings(TenantScopedMixin, Base):
    """One row per tenant — upsert on PUT /api/v1/settings."""

    __tablename__ = "facility_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Resource caps
    water_daily_limit_L: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_reserve_buffer_L: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_daily_limit_kWh: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_peak_load_kW: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_generation_kWh: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Workforce
    headcount_morning: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headcount_evening: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headcount_night: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Financial
    monthly_budget_INR: Mapped[float | None] = mapped_column(Float, nullable=True)
    electricity_rate_per_kWh: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_rate_per_1000L: Mapped[float | None] = mapped_column(Float, nullable=True)
    labor_cost_per_shift: Mapped[float | None] = mapped_column(Float, nullable=True)
    hauling_fee_per_ton: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Revenue
    plastic_yield_per_ton_INR: Mapped[float | None] = mapped_column(Float, nullable=True)
    compost_yield_per_ton_INR: Mapped[float | None] = mapped_column(Float, nullable=True)
    metal_yield_per_ton_INR: Mapped[float | None] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
