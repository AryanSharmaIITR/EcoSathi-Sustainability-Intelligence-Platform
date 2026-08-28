from fastapi import APIRouter

from app.api.v1.routes import (
    actions,
    alerts,
    classification,
    health,
    moe,
    recommend,
    reports,
    settings,
    tenants,
    usage,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tenants.router)
api_router.include_router(classification.router)
api_router.include_router(recommend.router)
api_router.include_router(moe.router)
api_router.include_router(usage.router)
api_router.include_router(actions.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
api_router.include_router(alerts.router)
