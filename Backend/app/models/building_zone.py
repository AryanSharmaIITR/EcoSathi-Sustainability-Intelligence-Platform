import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class BuildingZone(TenantScopedMixin, Base):
    """Facility zones/buildings — multiple rows per tenant."""

    __tablename__ = "building_zones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_capacity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    machinery: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
