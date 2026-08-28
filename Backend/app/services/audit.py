import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_ai_output(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    endpoint: str,
    model_name: str,
    confidence: float | None,
    input_ref: str,
    output: dict,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        endpoint=endpoint,
        model_name=model_name,
        confidence=confidence,
        input_ref=input_ref,
        output=output,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
