import csv
import datetime
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.models.usage_record import DailyWeather, UsageRecord
from app.schemas.telemetry_schema import TelemetrySnapshot
from app.schemas.usage import UsageRecordCreate, UsageUploadResponse
from app.services.telemetry import build_telemetry_snapshot

router = APIRouter(prefix="/usage", tags=["usage"])
logger = logging.getLogger(__name__)

_MAX_CSV_BYTES = 5 * 1024 * 1024


async def _insert_records(
    db: AsyncSession, tenant: Tenant, records: list[UsageRecordCreate]
) -> UsageUploadResponse:
    inserted = 0
    errors: list[str] = []
    weather_seen: dict[datetime.date, tuple[float, float]] = {}

    for i, record in enumerate(records):
        db.add(
            UsageRecord(
                tenant_id=tenant.id,
                building=record.building,
                resource_type=record.resource_type,
                reading_date=record.reading_date,
                value=record.value,
                unit=record.unit,
            )
        )
        inserted += 1
        if record.avg_temp_c is not None and record.rainfall_mm is not None:
            weather_seen[record.reading_date] = (record.avg_temp_c, record.rainfall_mm)

    for reading_date, (avg_temp_c, rainfall_mm) in weather_seen.items():
        db.add(
            DailyWeather(
                tenant_id=tenant.id,
                reading_date=reading_date,
                avg_temp_c=avg_temp_c,
                rainfall_mm=rainfall_mm,
            )
        )

    await db.commit()
    return UsageUploadResponse(inserted_count=inserted, skipped_count=len(errors), errors=errors)


@router.post("/records", response_model=UsageUploadResponse)
async def create_usage_records(
    records: list[UsageRecordCreate],
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> UsageUploadResponse:
    return await _insert_records(db, tenant, records)


@router.post("/upload-csv", response_model=UsageUploadResponse)
async def upload_usage_csv(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> UsageUploadResponse:
    """CSV columns: building, resource_type, reading_date, value, unit,
    and optionally avg_temp_c, rainfall_mm (applied once per date)."""
    raw = await file.read()
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV exceeds 5MB limit.")

    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    records: list[UsageRecordCreate] = []
    errors: list[str] = []
    for line_num, row in enumerate(reader, start=2):
        try:
            records.append(
                UsageRecordCreate(
                    building=row["building"],
                    resource_type=row["resource_type"],
                    reading_date=row["reading_date"],
                    value=float(row["value"]),
                    unit=row["unit"],
                    avg_temp_c=float(row["avg_temp_c"]) if row.get("avg_temp_c") else None,
                    rainfall_mm=float(row["rainfall_mm"]) if row.get("rainfall_mm") else None,
                )
            )
        except (KeyError, ValueError, ValidationError) as exc:
            errors.append(f"Row {line_num}: {exc}")

    if not records and errors:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No valid rows. First error: {errors[0]}")

    result = await _insert_records(db, tenant, records)
    result.errors = errors + result.errors
    result.skipped_count = len(errors)
    return result


@router.get("", response_model=TelemetrySnapshot)
async def get_usage(
    period_start: datetime.date | None = None,
    period_end: datetime.date | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> TelemetrySnapshot:
    """Returns the same TelemetrySnapshot shape the resource-planning agent
    consumes — real data computed from stored UsageRecord/DailyWeather
    rows, not fabricated. Defaults to the last 7 days."""
    if period_end is None:
        period_end = datetime.datetime.now(tz=datetime.UTC).date()
    if period_start is None:
        period_start = period_end - datetime.timedelta(days=6)
    if period_start > period_end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "period_start must be before period_end.")

    return await build_telemetry_snapshot(
        db, tenant_id=tenant.id, period_start=period_start, period_end=period_end
    )
