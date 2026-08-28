import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.action import Action
from app.models.tenant import Tenant
from app.schemas.action import ActionListResponse, ActionRead, ActionStats, ActionUpdate

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=ActionListResponse)
async def list_actions(
    page: int = 1,
    page_size: int = 10,
    status_filter: str | None = None,
    category: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ActionListResponse:
    """Real, persisted actions — created by POST /api/v1/recommend from
    the orchestration agent's actual output. Nothing here is fabricated
    by the frontend or seeded by hand."""
    result = await db.execute(
        select(Action).where(Action.tenant_id == tenant.id).order_by(Action.created_at.desc())
    )
    rows = result.scalars().all()

    now = datetime.datetime.now(tz=datetime.UTC)
    week_ago = now - datetime.timedelta(days=7)
    this_week_count = sum(1 for r in rows if r.created_at >= week_ago)

    stats = ActionStats(
        total_actions=len(rows),
        in_progress_count=sum(1 for r in rows if r.status == "in_progress"),
        pending_count=sum(1 for r in rows if r.status == "pending"),
        completed_count=sum(1 for r in rows if r.status == "completed"),
        total_actions_wow=this_week_count,
        estimated_monthly_impact_total=sum(
            r.estimated_monthly_impact for r in rows if r.estimated_monthly_impact
        ),
    )

    if status_filter and status_filter.lower() != "all":
        rows = [r for r in rows if r.status == status_filter.lower()]
    if category and category.lower() != "all":
        rows = [r for r in rows if r.category == category.lower()]

    total_items = len(rows)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    return ActionListResponse(
        stats=stats,
        items=[ActionRead.model_validate(r) for r in page_rows],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    action_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Action).where(Action.id == action_id, Action.tenant_id == tenant.id)
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found.")
    await db.delete(action)
    await db.commit()


@router.patch("/{action_id}", response_model=ActionRead)
async def update_action(
    action_id: str,
    payload: ActionUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ActionRead:
    result = await db.execute(
        select(Action).where(Action.id == action_id, Action.tenant_id == tenant.id)
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found.")

    if payload.status is not None:
        action.status = payload.status
        if payload.status == "completed":
            action.progress_pct = 100
            action.completed_at = datetime.datetime.now(tz=datetime.UTC)
    if payload.progress_pct is not None:
        action.progress_pct = payload.progress_pct
        if payload.progress_pct == 100 and action.status != "completed":
            action.status = "completed"
            action.completed_at = datetime.datetime.now(tz=datetime.UTC)

    await db.commit()
    await db.refresh(action)
    return ActionRead.model_validate(action)
