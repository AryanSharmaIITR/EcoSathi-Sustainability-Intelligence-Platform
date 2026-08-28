import datetime
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.groq_client import classify_waste_image
from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.schemas.waste import WasteClassificationResponse
from app.schemas.waste_scan import (
    WasteScanHistoryResponse,
    WasteScanItem,
    WasteScanStats,
)
from app.services.audit import record_ai_output

router = APIRouter(prefix="/classify", tags=["classification"])
logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # Groq's per-request image size limit
_NON_RECYCLABLE_CATEGORIES = {"landfill", "hazardous", "e-waste"}


@router.post("", response_model=WasteClassificationResponse)
async def classify_waste(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> WasteClassificationResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image.")

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image exceeds 20MB limit."
        )

    try:
        result = await classify_waste_image(image_bytes, file.content_type)
    except Exception as exc:
        logger.exception("Groq classification call failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Classification provider error: {exc}"
        ) from exc

    await record_ai_output(
        db,
        tenant_id=tenant.id,
        endpoint="/api/v1/classify",
        model_name=result["model"],
        confidence=result["confidence"],
        input_ref=file.filename or "unnamed-upload",
        output=result,
    )

    return WasteClassificationResponse(
        item_name=result["item_name"],
        category=result["category"],
        disposal_instructions=result["disposal_instructions"],
        confidence=result["confidence"],
        source=result["model"],
    )


@router.get("/history", response_model=WasteScanHistoryResponse)
async def get_classification_history(
    page: int = 1,
    page_size: int = 10,
    category: str | None = None,
    search: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> WasteScanHistoryResponse:
    """Real waste-scan history, built entirely from AuditLog rows written
    by POST /api/v1/classify — no separate table, no fabricated data."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant.id, AuditLog.endpoint == "/api/v1/classify")
        .order_by(AuditLog.created_at.desc())
    )
    rows = result.scalars().all()

    now = datetime.datetime.now(tz=datetime.UTC)
    week_ago = now - datetime.timedelta(days=7)
    two_weeks_ago = now - datetime.timedelta(days=14)
    this_week_count = sum(1 for r in rows if r.created_at >= week_ago)
    last_week_count = sum(1 for r in rows if two_weeks_ago <= r.created_at < week_ago)
    wow_pct = (
        round((this_week_count - last_week_count) / last_week_count * 100, 1)
        if last_week_count
        else None
    )

    confidences = [r.confidence for r in rows if r.confidence is not None]
    stats = WasteScanStats(
        total_scans=len(rows),
        recyclable_count=sum(1 for r in rows if r.output.get("category") == "recyclable"),
        compostable_count=sum(1 for r in rows if r.output.get("category") == "compostable"),
        non_recyclable_count=sum(
            1 for r in rows if r.output.get("category") in _NON_RECYCLABLE_CATEGORIES
        ),
        avg_confidence=round(sum(confidences) / len(confidences), 2) if confidences else None,
        total_scans_wow_pct=wow_pct,
    )

    if category and category.lower() != "all":
        rows = [r for r in rows if r.output.get("category") == category.lower()]
    if search:
        needle = search.lower()
        rows = [r for r in rows if needle in str(r.output.get("item_name", "")).lower()]

    total_items = len(rows)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    items = [
        WasteScanItem(
            id=r.id,
            item_name=r.output.get("item_name", "Unidentified item"),
            category=r.output.get("category", "landfill"),
            disposal_instructions=r.output.get("disposal_instructions", ""),
            confidence=r.confidence,
            source=r.model_name,
            input_ref=r.input_ref,
            scanned_at=r.created_at,
        )
        for r in page_rows
    ]

    return WasteScanHistoryResponse(
        stats=stats,
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )
