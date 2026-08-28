import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent.runner import run_recommendation_agent
from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.action import Action
from app.models.tenant import Tenant
from app.schemas.recommendation import ActionItem, ActionItemWithId, RecommendationResponse
from app.services.audit import record_ai_output

router = APIRouter(prefix="/recommend", tags=["recommendation"])
logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = 20 * 1024 * 1024


@router.post("", response_model=RecommendationResponse)
async def recommend(
    file: UploadFile | None = File(default=None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    image_bytes: bytes | None = None
    image_content_type: str | None = None
    if file is not None:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image.")
        image_bytes = await file.read()
        if len(image_bytes) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image exceeds 20MB limit."
            )
        image_content_type = file.content_type

    try:
        result = await run_recommendation_agent(
            tenant_id=str(tenant.id),
            image_bytes=image_bytes,
            image_content_type=image_content_type,
        )
    except Exception as exc:
        logger.exception("Recommendation agent failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Orchestration agent error: {exc}"
        ) from exc

    input_ref = file.filename if file is not None else "no-image"

    # Every tool the agent actually invoked is independently traceable,
    # in addition to the final orchestrated decision below.
    for step in result["trace"]:
        step_result = step["result"]
        await record_ai_output(
            db,
            tenant_id=tenant.id,
            endpoint=f"/api/v1/recommend:{step['tool']}",
            model_name=step_result.get("model", result["model"])
            if isinstance(step_result, dict)
            else result["model"],
            confidence=step_result.get("confidence") if isinstance(step_result, dict) else None,
            input_ref=input_ref,
            output=step_result,
        )

    await record_ai_output(
        db,
        tenant_id=tenant.id,
        endpoint="/api/v1/recommend",
        model_name=result["model"],
        confidence=None,
        input_ref=input_ref,
        output={"actions": result["actions"]},
    )

    # Persist each recommended action as a real, trackable row — the
    # Actions page reads these back, it never fabricates its own data.
    actions = [ActionItem.model_validate(a) for a in result["actions"]]
    db_rows = []
    for action in actions:
        row = Action(
            tenant_id=tenant.id,
            title=action.title,
            rationale=action.rationale,
            category=action.category,
            priority=action.priority,
            status="pending",
            progress_pct=0,
            estimated_monthly_impact=action.estimated_monthly_impact,
            source=result["model"],
            recommended_steps=[],
        )
        db.add(row)
        db_rows.append(row)
    await db.commit()
    # Refresh to materialise the auto-generated UUIDs before returning them.
    for row in db_rows:
        await db.refresh(row)

    actions_with_ids = [
        ActionItemWithId(**action.model_dump(), id=row.id)
        for action, row in zip(actions, db_rows)
    ]

    return RecommendationResponse(
        actions=actions_with_ids,
        confidence=None,
        source=result["model"],
    )
