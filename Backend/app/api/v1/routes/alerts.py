import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.alert_incident import AlertIncident
from app.models.facility_settings import FacilitySettings
from app.models.tenant import Tenant
from app.schemas.alert import AlertIncidentRead, AlertIncidentUpdate, AlertStats, AlertsListResponse
from app.services import alert_engine
from app.services.telemetry import build_telemetry_snapshot

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsListResponse)
async def list_alerts(
    alert_status: str | None = None,
    severity: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> AlertsListResponse:
    """List alert incidents for this tenant, with optional filters."""
    q = select(AlertIncident).where(AlertIncident.tenant_id == tenant.id)
    if alert_status and alert_status.lower() != "all":
        q = q.where(AlertIncident.status == alert_status.lower())
    if severity and severity.lower() != "all":
        q = q.where(AlertIncident.severity == severity.lower())
    q = q.order_by(AlertIncident.triggered_at.desc())

    result = await db.execute(q)
    rows = result.scalars().all()

    # Stats are always over active alerts (not filtered)
    active_result = await db.execute(
        select(AlertIncident).where(
            AlertIncident.tenant_id == tenant.id,
            AlertIncident.status == "active",
        )
    )
    active_rows = active_result.scalars().all()

    stats = AlertStats(
        total_active=len(active_rows),
        critical_count=sum(1 for r in active_rows if r.severity == "critical"),
        high_count=sum(1 for r in active_rows if r.severity == "high"),
        warning_count=sum(1 for r in active_rows if r.severity == "warning"),
        info_count=sum(1 for r in active_rows if r.severity == "info"),
    )

    return AlertsListResponse(
        stats=stats,
        items=[AlertIncidentRead.model_validate(r) for r in rows],
    )


@router.post("/evaluate", response_model=list[AlertIncidentRead])
async def evaluate_alerts(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[AlertIncidentRead]:
    """Run the alert engine against current telemetry and settings.
    Returns any newly triggered alerts."""
    # Load current settings
    result = await db.execute(
        select(FacilitySettings).where(FacilitySettings.tenant_id == tenant.id)
    )
    settings = result.scalar_one_or_none()

    if settings is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No facility settings configured. Set up constraints via PUT /api/v1/settings first.",
        )

    # Load latest telemetry snapshot (last 30 days)
    now = dt.datetime.now(tz=dt.UTC).date()
    period_start = now - dt.timedelta(days=29)
    snapshot = await build_telemetry_snapshot(
        db, tenant_id=tenant.id, period_start=period_start, period_end=now
    )

    new_alerts = await alert_engine.evaluate_constraints(
        db=db,
        tenant_id=tenant.id,
        snapshot=snapshot,
        settings=settings,
    )
    return [AlertIncidentRead.model_validate(a) for a in new_alerts]


@router.patch("/{alert_id}", response_model=AlertIncidentRead)
async def update_alert(
    alert_id: uuid.UUID,
    payload: AlertIncidentUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> AlertIncidentRead:
    """Acknowledge or resolve an alert."""
    result = await db.execute(
        select(AlertIncident).where(
            AlertIncident.id == alert_id, AlertIncident.tenant_id == tenant.id
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found.")

    new_status = payload.status.lower()
    if new_status not in ("acknowledged", "resolved"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "status must be 'acknowledged' or 'resolved'.",
        )

    alert.status = new_status
    now_ts = dt.datetime.now(dt.UTC)
    if new_status == "acknowledged":
        alert.acknowledged_at = now_ts
    elif new_status == "resolved":
        alert.resolved_at = now_ts
        if alert.acknowledged_at is None:
            alert.acknowledged_at = now_ts

    await db.commit()
    await db.refresh(alert)
    return AlertIncidentRead.model_validate(alert)
