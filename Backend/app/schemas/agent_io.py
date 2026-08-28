"""Pydantic schemas for the Mixture-of-Experts (MoE) multi-agent system.

Each agent has a typed input and output schema.  The supervisor collects
per-agent outputs and synthesises them into a single MoEResponse that the
API surface returns to callers.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.base import AIGeneratedResponse
from app.schemas.telemetry_schema import (
    TelemetrySnapshot,
)

# ---------------------------------------------------------------------------
# Shared / generic
# ---------------------------------------------------------------------------


class TraceStep(BaseModel):
    """One tool invocation captured in the agent execution trace."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Supervisor / router
# ---------------------------------------------------------------------------


class SupervisorRouting(BaseModel):
    """Routing decision produced by the Central AI Supervisor."""

    requires_waste_agent: bool = Field(
        description="True when the query involves waste classification, SOPs or compliance."
    )
    requires_resource_agent: bool = Field(
        description="True when the query involves facility resources, telemetry or planning."
    )
    routing_rationale: str = Field(
        description="Brief explanation of why the supervisor chose this routing."
    )


class MoERequest(BaseModel):
    """Input to the MoE orchestrator."""

    query: str = Field(description="Natural-language question or task from the user.")
    tenant_id: str
    telemetry: TelemetrySnapshot | None = Field(
        default=None,
        description="Optional live telemetry context injected by the caller.",
    )
    image_base64: str | None = Field(
        default=None,
        description="Base-64 encoded image for waste classification (optional).",
    )
    image_content_type: str | None = None


# ---------------------------------------------------------------------------
# Expert Agent 1 — Waste & Compliance
# ---------------------------------------------------------------------------


class WasteCategory(BaseModel):
    name: str = Field(description="Canonical category name, e.g. 'e-waste'.")
    stream: Literal[
        "organic", "plastic", "e-waste", "hazardous", "industrial", "recyclable", "landfill", "other"
    ]


class RegulatoryReference(BaseModel):
    """A single cited regulatory document or section."""

    title: str = Field(description="Document title, e.g. 'E-Waste Management Rules 2022'.")
    section: str | None = Field(default=None, description="Specific rule/section number.")
    authority: str = Field(
        default="Government of India",
        description="Issuing authority (CPCB, MoEFCC, etc.).",
    )
    relevance_snippet: str = Field(
        description="Short quote or paraphrase from the document relevant to this result."
    )


class WasteComplianceOutput(BaseModel):
    """Structured output from Expert Agent 1: Waste & Compliance Engine."""

    item_name: str
    category: WasteCategory
    recycling_sop: list[str] = Field(
        description="Ordered step-by-step recycling / handling instructions."
    )
    regulatory_references: list[RegulatoryReference] = Field(
        default_factory=list,
        description="GoI / CPCB regulatory citations supporting the SOP.",
    )
    compliance_notes: str | None = Field(
        default=None,
        description="Any notable legal obligations, EPR responsibilities, or penalties.",
    )
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    trace: list[TraceStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Expert Agent 2 — Resource & Ops Planning
# ---------------------------------------------------------------------------


class FacilityLoad(BaseModel):
    """Resource load snapshot for a single facility / building."""

    building: str
    water_usage_L: float = Field(description="Water consumption in litres for the period.")
    energy_usage_kWh: float = Field(description="Energy consumption in kWh for the period.")
    waste_scanned_count: int = Field(default=0)
    available_buffer_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Estimated spare operational capacity as a percentage.",
    )


class ResourceForecast(BaseModel):
    """Demand forecast for a specific resource."""

    resource: Literal["water", "energy", "labor"]
    unit: str = Field(description="Unit of measurement (L, kWh, person-hours).")
    forecasted_requirement: float
    current_actual: float | None = None
    variance_pct: float | None = Field(
        default=None,
        description="Percentage over/under current actual. Positive = over-budget.",
    )
    forecast_basis: str = Field(description="Brief explanation of how the forecast was derived.")


class WorkloadAllocation(BaseModel):
    """Recommendation for where to assign a processing task."""

    recommended_building: str
    reason: str
    alternative_buildings: list[str] = Field(default_factory=list)


class ResourcePlanningOutput(BaseModel):
    """Structured output from Expert Agent 2: Resource & Ops Planning Engine."""

    facility_loads: list[FacilityLoad] = Field(default_factory=list)
    forecasts: list[ResourceForecast] = Field(default_factory=list)
    workload_allocation: WorkloadAllocation | None = None
    planning_notes: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    trace: list[TraceStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Final MoE response
# ---------------------------------------------------------------------------


class MoEResponse(AIGeneratedResponse):
    """Synthesised response returned by the Central AI Supervisor after
    collecting outputs from whichever expert agents were invoked."""

    routing: SupervisorRouting
    waste_compliance: WasteComplianceOutput | None = None
    resource_planning: ResourcePlanningOutput | None = None
    synthesis: str = Field(
        description="Supervisor's coherent natural-language summary combining all agent outputs."
    )
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked action items (title, priority, rationale) for the facilities manager.",
    )
    trace: list[TraceStep] = Field(
        default_factory=list,
        description="Full execution trace across all agents for audit logging.",
    )


