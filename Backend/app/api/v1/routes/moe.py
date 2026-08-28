"""FastAPI route for the MoE multi-agent system.

Endpoint: POST /api/v1/moe/query

Accepts:
  - JSON body: MoERequest (query, optional telemetry snapshot)
  - Optional form-field image upload (multipart) for waste classification

Returns:
  - MoEResponse with routing metadata, expert agent outputs,
    synthesised summary, ranked actions, and execution trace.

Every agent tool invocation in the trace is individually audit-logged
in addition to the overall MoE response, preserving the spec's
"every AI output must be traceable" requirement.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import run_moe_pipeline
from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.agent_io import MoERequest, MoEResponse
from app.schemas.telemetry_schema import TelemetrySnapshot
from app.services.audit import record_ai_output

router = APIRouter(prefix="/moe", tags=["moe"])
logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = 20 * 1024 * 1024


@router.post("/query", response_model=MoEResponse)
async def moe_query(
    request: MoERequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> MoEResponse:
    """Run the full MoE multi-agent pipeline for a natural-language query.

    The request body accepts an optional ``TelemetrySnapshot`` for the
    resource planning agent, and an optional base64-encoded image for
    the waste classification agent.

    Tenant isolation is enforced: ``request.tenant_id`` is overwritten
    with the authenticated tenant's ID so a caller cannot cross-tenant.
    """
    # Enforce tenant isolation — overwrite any tenant_id in the request
    # body with the authenticated tenant's actual ID.
    safe_request = MoERequest(
        query=request.query,
        tenant_id=str(tenant.id),
        telemetry=request.telemetry,
        image_base64=request.image_base64,
        image_content_type=request.image_content_type,
    )

    try:
        result = await run_moe_pipeline(safe_request)
    except Exception as exc:
        logger.exception("MoE pipeline raised an exception")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"MoE pipeline error: {exc}",
        ) from exc

    # --- Audit logging ---
    # Log each individual agent tool call from the trace
    for step in result.trace:
        step_result = step.result
        await record_ai_output(
            db,
            tenant_id=tenant.id,
            endpoint=f"/api/v1/moe/query:{step.tool}",
            # AuditLog.model_name is NOT NULL, but not every trace step is an
            # LLM call (routing/synthesis/RAG/facility-tool steps don't set
            # "model") — fall back to the tool name so this never crashes.
            model_name=(step_result.get("model") if isinstance(step_result, dict) else None)
            or step.tool,
            confidence=step_result.get("confidence") if isinstance(step_result, dict) else None,
            input_ref=f"query:{safe_request.query[:80]}",
            output=step_result if isinstance(step_result, dict) else {"value": str(step_result)},
        )

    # Log the final synthesised MoE response
    await record_ai_output(
        db,
        tenant_id=tenant.id,
        endpoint="/api/v1/moe/query",
        model_name=result.source,
        confidence=result.confidence,
        input_ref=f"query:{safe_request.query[:80]}",
        output={
            "synthesis": result.synthesis,
            "action_count": len(result.actions),
            "waste_agent_invoked": result.waste_compliance is not None,
            "resource_agent_invoked": result.resource_planning is not None,
        },
    )

    return result


@router.post("/query-with-image", response_model=MoEResponse)
async def moe_query_with_image(
    query: str,
    file: UploadFile | None = File(default=None),
    telemetry_json: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> MoEResponse:
    """Multipart variant of the MoE query endpoint that accepts a file upload
    alongside the query text.

    Use this endpoint when the client wants to upload an image for waste
    classification as part of a broader MoE query, without base64-encoding
    the image in the JSON body.

    Parameters (form fields):
      - query: The natural-language question.
      - file: Optional image file (jpg/png etc.).
      - telemetry_json: Optional JSON string of a TelemetrySnapshot.
    """
    import base64
    import json as _json

    image_b64: str | None = None
    image_content_type: str | None = None

    if file is not None:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image.")
        raw = await file.read()
        if len(raw) > _MAX_IMAGE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image exceeds 20MB limit.")
        image_b64 = base64.b64encode(raw).decode("utf-8")
        image_content_type = file.content_type

    telemetry: TelemetrySnapshot | None = None
    if telemetry_json:
        try:
            telemetry = TelemetrySnapshot.model_validate(_json.loads(telemetry_json))
        except (ValueError, TypeError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid telemetry_json payload.")

    moe_request = MoERequest(
        query=query,
        tenant_id=str(tenant.id),
        telemetry=telemetry,
        image_base64=image_b64,
        image_content_type=image_content_type,
    )

    try:
        result = await run_moe_pipeline(moe_request)
    except Exception as exc:
        logger.exception("MoE pipeline (with-image) raised an exception")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"MoE pipeline error: {exc}") from exc

    # Audit logging (same pattern as /query)
    for step in result.trace:
        step_result = step.result
        await record_ai_output(
            db,
            tenant_id=tenant.id,
            endpoint=f"/api/v1/moe/query-with-image:{step.tool}",
            # AuditLog.model_name is NOT NULL, but not every trace step is an
            # LLM call (routing/synthesis/RAG/facility-tool steps don't set
            # "model") — fall back to the tool name so this never crashes.
            model_name=(step_result.get("model") if isinstance(step_result, dict) else None)
            or step.tool,
            confidence=step_result.get("confidence") if isinstance(step_result, dict) else None,
            input_ref=f"query:{query[:80]}|image={file.filename if file else 'none'}",
            output=step_result if isinstance(step_result, dict) else {"value": str(step_result)},
        )

    await record_ai_output(
        db,
        tenant_id=tenant.id,
        endpoint="/api/v1/moe/query-with-image",
        model_name=result.source,
        confidence=result.confidence,
        input_ref=f"query:{query[:80]}",
        output={
            "synthesis": result.synthesis,
            "action_count": len(result.actions),
            "waste_agent_invoked": result.waste_compliance is not None,
            "resource_agent_invoked": result.resource_planning is not None,
        },
    )

    return result
