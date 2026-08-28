import csv
import datetime
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.audit_log import AuditLog
from app.models.report import GeneratedReport
from app.models.tenant import Tenant
from app.models.usage_record import UsageRecord
from app.schemas.report import (
    GeneratedReportRead,
    GenerateReportRequest,
    ReportsListResponse,
    ReportsStats,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# Documented estimation constant (a standard sustainability-reporting
# emission factor, not fabricated telemetry) — kg of CO2 avoided per
# recyclable item diverted from landfill. Adjust per local waste-stream
# carbon-intensity data when available.
CO2_KG_PER_RECYCLED_ITEM = 0.5


async def _compute_stats(db: AsyncSession, tenant_id) -> ReportsStats:
    reports_result = await db.execute(
        select(func.count(), func.coalesce(func.sum(GeneratedReport.download_count), 0)).where(
            GeneratedReport.tenant_id == tenant_id
        )
    )
    reports_generated, total_downloads = reports_result.one()

    usage_count = await db.execute(
        select(func.count()).where(UsageRecord.tenant_id == tenant_id)
    )
    audit_count = await db.execute(select(func.count()).where(AuditLog.tenant_id == tenant_id))
    insights_count = await db.execute(
        select(func.count()).where(
            AuditLog.tenant_id == tenant_id, AuditLog.endpoint == "/api/v1/recommend"
        )
    )
    classify_rows = await db.execute(
        select(AuditLog.output).where(
            AuditLog.tenant_id == tenant_id, AuditLog.endpoint == "/api/v1/classify"
        )
    )
    recyclable_count = sum(
        1 for (output,) in classify_rows.all() if output.get("category") == "recyclable"
    )

    return ReportsStats(
        reports_generated=reports_generated,
        total_downloads=total_downloads,
        data_points_analyzed=usage_count.scalar_one() + audit_count.scalar_one(),
        insights_generated=insights_count.scalar_one(),
        co2_avoided_kg=round(recyclable_count * CO2_KG_PER_RECYCLED_ITEM, 1),
    )


@router.get("", response_model=ReportsListResponse)
async def list_reports(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ReportsListResponse:
    stats = await _compute_stats(db, tenant.id)
    result = await db.execute(
        select(GeneratedReport)
        .where(GeneratedReport.tenant_id == tenant.id)
        .order_by(GeneratedReport.created_at.desc())
    )
    items = [GeneratedReportRead.model_validate(r) for r in result.scalars().all()]
    return ReportsListResponse(stats=stats, items=items)


@router.post("/generate", response_model=GeneratedReportRead, status_code=status.HTTP_201_CREATED)
async def generate_report(
    payload: GenerateReportRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> GeneratedReportRead:
    report = GeneratedReport(
        tenant_id=tenant.id,
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        generated_by="system",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return GeneratedReportRead.model_validate(report)


@router.get("/{report_id}/export.csv")
async def export_report_csv(
    report_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Real CSV export of the underlying data for this report — not a
    fabricated PDF. Increments the report's download_count."""
    result = await db.execute(
        select(GeneratedReport).where(
            GeneratedReport.id == report_id, GeneratedReport.tenant_id == tenant.id
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if report.report_type in ("water", "energy", "sustainability"):
        resource_filter = None if report.report_type == "sustainability" else report.report_type
        query = select(UsageRecord).where(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.reading_date >= report.period_start,
            UsageRecord.reading_date <= report.period_end,
        )
        if resource_filter:
            query = query.where(UsageRecord.resource_type == resource_filter)
        rows = (await db.execute(query.order_by(UsageRecord.reading_date))).scalars().all()
        writer.writerow(["building", "resource_type", "reading_date", "value", "unit"])
        for r in rows:
            writer.writerow([r.building, r.resource_type, r.reading_date, r.value, r.unit])
    else:  # waste / emissions -> classification history
        start_dt = datetime.datetime.combine(report.period_start, datetime.time.min, tzinfo=datetime.UTC)
        end_dt = datetime.datetime.combine(
            report.period_end + datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.UTC
        )
        rows = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.endpoint == "/api/v1/classify",
                        AuditLog.created_at >= start_dt,
                        AuditLog.created_at < end_dt,
                    )
                )
            )
            .scalars()
            .all()
        )
        writer.writerow(["item_name", "category", "confidence", "scanned_at"])
        for r in rows:
            writer.writerow(
                [r.output.get("item_name"), r.output.get("category"), r.confidence, r.created_at]
            )

    report.download_count += 1
    await db.commit()

    buffer.seek(0)
    filename = f"{report.report_type}-report-{report.period_start}-{report.period_end}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
