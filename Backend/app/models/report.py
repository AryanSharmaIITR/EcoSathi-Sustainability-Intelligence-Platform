import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.tenant import TenantScopedMixin


class GeneratedReport(TenantScopedMixin, Base):
    """A record of one report-generation event. The report's actual
    content is computed on demand from real tables (usage_records,
    audit_logs, actions) at export time — this row just tracks that a
    report of this type/period was generated and how many times it was
    downloaded, exactly like the Reports Library / Recent Reports panels
    in the mockup."""

    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
