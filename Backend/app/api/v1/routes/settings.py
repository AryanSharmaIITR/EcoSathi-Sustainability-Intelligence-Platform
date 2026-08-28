import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.building_zone import BuildingZone
from app.models.facility_settings import FacilitySettings
from app.models.tenant import Tenant
from app.models.usage_record import UsageRecord
from app.schemas.facility_settings import (
    BuildingZoneCreate,
    BuildingZoneRead,
    BuildingZoneUpdate,
    FacilitySettingsRead,
    FacilitySettingsUpdate,
)

router = APIRouter(prefix="/settings", tags=["settings"])

# ── FacilitySettings ────────────────────────────────────────────────────────


@router.get("", response_model=FacilitySettingsRead)
async def get_settings(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> FacilitySettingsRead:
    """Return existing settings or a default empty row."""
    result = await db.execute(
        select(FacilitySettings).where(FacilitySettings.tenant_id == tenant.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        # Return defaults without persisting
        now = datetime.now(UTC)
        return FacilitySettingsRead(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            updated_at=now,
        )
    return FacilitySettingsRead.model_validate(row)


@router.put("", response_model=FacilitySettingsRead)
async def upsert_settings(
    payload: FacilitySettingsUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> FacilitySettingsRead:
    """Upsert facility settings (one row per tenant)."""
    result = await db.execute(
        select(FacilitySettings).where(FacilitySettings.tenant_id == tenant.id)
    )
    row = result.scalar_one_or_none()

    update_data = payload.model_dump(exclude_unset=True)

    if row is None:
        row = FacilitySettings(tenant_id=tenant.id, **update_data)
        db.add(row)
    else:
        for field, value in update_data.items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(row)
    return FacilitySettingsRead.model_validate(row)


# ── BuildingZones ───────────────────────────────────────────────────────────


@router.get("/zones", response_model=list[BuildingZoneRead])
async def list_zones(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[BuildingZoneRead]:
    result = await db.execute(
        select(BuildingZone)
        .where(BuildingZone.tenant_id == tenant.id)
        .order_by(BuildingZone.created_at)
    )
    rows = result.scalars().all()
    return [BuildingZoneRead.model_validate(r) for r in rows]


@router.post("/zones", response_model=BuildingZoneRead, status_code=status.HTTP_201_CREATED)
async def create_zone(
    payload: BuildingZoneCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> BuildingZoneRead:
    zone = BuildingZone(tenant_id=tenant.id, **payload.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return BuildingZoneRead.model_validate(zone)


@router.patch("/zones/{zone_id}", response_model=BuildingZoneRead)
async def update_zone(
    zone_id: uuid.UUID,
    payload: BuildingZoneUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> BuildingZoneRead:
    result = await db.execute(
        select(BuildingZone).where(
            BuildingZone.id == zone_id, BuildingZone.tenant_id == tenant.id
        )
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Building zone not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    zone.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(zone)
    return BuildingZoneRead.model_validate(zone)


@router.post("/zones/sync-from-usage", response_model=list[BuildingZoneRead])
async def sync_zones_from_usage(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[BuildingZoneRead]:
    """Create a zone (with no capacity/area/machinery set) for every building
    name that appears in uploaded usage records but has no matching zone yet.
    Lets Settings → Infrastructure catch up with data already visible on the
    Usage dashboard instead of requiring manual re-entry of names that were
    already typed once into a usage CSV."""
    existing_result = await db.execute(
        select(BuildingZone.name).where(BuildingZone.tenant_id == tenant.id)
    )
    existing_names = {row[0] for row in existing_result.all()}

    usage_result = await db.execute(
        select(UsageRecord.building)
        .where(UsageRecord.tenant_id == tenant.id)
        .distinct()
    )
    usage_names = {row[0] for row in usage_result.all()}

    missing_names = sorted(usage_names - existing_names)
    new_zones = [BuildingZone(tenant_id=tenant.id, name=name) for name in missing_names]
    db.add_all(new_zones)
    await db.commit()
    for zone in new_zones:
        await db.refresh(zone)

    return [BuildingZoneRead.model_validate(z) for z in new_zones]


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(BuildingZone).where(
            BuildingZone.id == zone_id, BuildingZone.tenant_id == tenant.id
        )
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Building zone not found.")
    await db.delete(zone)
    await db.commit()
