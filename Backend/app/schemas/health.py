from typing import Literal

from app.schemas.base import APIResponse


class HealthResponse(APIResponse):
    status: Literal["ok"]
    environment: str
