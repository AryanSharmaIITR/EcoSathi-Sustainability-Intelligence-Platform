from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Base envelope for non-AI-derived API responses."""


class AIGeneratedResponse(APIResponse):
    """Base envelope for any response whose payload is produced or
    influenced by a model (vision/LLM classification, forecast, agent
    recommendation). Per the spec: 'every AI response needs a
    confidence/source field in the schema from day one' — subclass this
    rather than APIResponse for any such endpoint so the fields are
    structural, not just documented convention. Nullable until a real
    model is wired for that endpoint.
    """

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence score, 0-1. Null until a real model is wired.",
    )
    source: str | None = Field(
        default=None,
        description="Traceability pointer: model name/version, input artifact id, or data source.",
    )
