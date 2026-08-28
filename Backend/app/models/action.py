import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class Action(TenantScopedMixin, Base):
    """A recommended action, persisted so it can be tracked to completion
    (status/progress), not just a stateless agent response. Rows are
    created from the /recommend agent's real output — see
    app.api.v1.routes.recommend — never fabricated by the frontend."""

    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # water|energy|waste|general
    priority: Mapped[str] = mapped_column(String(20), nullable=False)  # high|medium|low
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_monthly_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)  # model/agent that generated it
    recommended_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
