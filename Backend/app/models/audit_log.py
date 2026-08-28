import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class AuditLog(TenantScopedMixin, Base):
    """Traceability record for every AI output shown to a tenant, per the
    spec's compliance requirement: 'traceable to its source (an input
    image, a data point, a model version)'. input_ref + model_name cover
    the source; output preserves exactly what was shown."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    output: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
