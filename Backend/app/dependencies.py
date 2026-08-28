import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant


async def get_current_tenant(
    x_tenant_id: uuid.UUID | None = Header(default=None, alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolves the tenant for this request. Every tenant-scoped route
    and query must depend on this and filter on tenant.id — this is the
    single seam that enforces tenant isolation (see
    app.models.tenant.TenantScopedMixin). Row-level scoping must never
    trust a tenant_id passed in a request body.

    The header-based resolution here is a deliberately visible stub:
    Phase 3 (per the spec) replaces/augments this with tenant derived
    from the authenticated user (e.g. a JWT claim), not a raw header.

    --- TENANT ENFORCEMENT TEMPORARILY DISABLED (dev/testing, by request) ---
    The spec calls tenant isolation a security requirement, not a nicety.
    Uncomment the block below and delete the fallback beneath it before
    anything resembling production.
    """
    # if x_tenant_id is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="X-Tenant-Id header is required.",
    #     )
    #
    # tenant = await db.scalar(
    #     select(Tenant).where(Tenant.id == x_tenant_id, Tenant.is_active.is_(True))
    # )
    # if tenant is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Unknown or inactive tenant.",
    #     )
    # return tenant

    if x_tenant_id is not None:
        tenant = await db.scalar(
            select(Tenant).where(Tenant.id == x_tenant_id, Tenant.is_active.is_(True))
        )
        if tenant is not None:
            return tenant

    # No header (or an unknown one) — auto-pick any active tenant so
    # endpoints keep working without requiring a header at all.
    tenant = await db.scalar(
        select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.created_at)
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenant exists yet — create one via POST /api/v1/tenants.",
        )
    return tenant
