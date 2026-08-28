"""Central AI Supervisor — MoE Router and Synthesis Layer.

Responsibilities
----------------
1. **Routing:** Analyse the incoming query and decide which expert agents
   to invoke (waste_compliance, resource_planning, or both).
2. **Parallel dispatch:** Run whichever expert agents are needed
   (concurrently where possible via asyncio.gather).
3. **Synthesis:** Merge the expert outputs into a single coherent response
   with ranked action items for the facilities manager.

The routing decision is made by a Groq LLM call that returns a small JSON
object.  All routing decisions are logged to the execution trace.

Design notes
------------
- The supervisor itself does not have a tool loop — it calls the experts as
  Python coroutines, not via tool specs.  This keeps the MoE boundary
  explicit and auditable.
- Each expert agent has its own internal LangGraph loop and trace.  The
  supervisor aggregates those traces into one top-level list.
"""

from __future__ import annotations

import asyncio
import json
import logging

from groq import AsyncGroq

from app.ai.agents.resource_planning_agent import run_resource_planning_agent
from app.ai.agents.waste_compliance_agent import run_waste_compliance_agent
from app.ai.json_utils import extract_json
from app.core.config import get_settings
from app.schemas.agent_io import (
    MoERequest,
    MoEResponse,
    ResourcePlanningOutput,
    SupervisorRouting,
    TraceStep,
    WasteComplianceOutput,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing prompt
# ---------------------------------------------------------------------------

_ROUTING_SYSTEM_PROMPT = """\
You are the routing layer of EcoSathi's multi-expert AI system.
Given a user query, decide which expert agents to activate:
  - waste_agent: handles waste classification, recycling SOPs, and GoI regulatory compliance
  - resource_agent: handles facility resource planning, telemetry analysis, energy/water/labor forecasting

Return ONLY a JSON object:
{
  "requires_waste_agent": <true|false>,
  "requires_resource_agent": <true|false>,
  "routing_rationale": "<one sentence explanation>"
}

Rules:
- If the query mentions any waste item, recycling, disposal, e-waste, composting, compliance,
  CPCB, EPR, or SOP → set requires_waste_agent = true.
- If the query mentions energy, water, power, usage, consumption, forecast, building, campus,
  facility, capacity, labor, or resource planning → set requires_resource_agent = true.
- When in doubt, activate both agents.
- Never output anything other than the JSON object.
"""

# ---------------------------------------------------------------------------
# Synthesis prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_SYSTEM_PROMPT = """\
You are EcoSathi's Central AI Supervisor. You have received structured outputs
from one or more expert agents. Synthesise them into:
1. A clear, actionable natural-language summary for a facilities manager.
2. A ranked list of action items.

Respond with ONLY a JSON object:
{
  "synthesis": "<coherent 2-4 sentence summary combining all agent findings>",
  "actions": [
    {
      "title": "<short action title>",
      "priority": "high" | "medium" | "low",
      "rationale": "<why this action is recommended>"
    }
  ]
}

Rules:
- Rank actions by impact — most critical first.
- Do not repeat information already in the synthesis as a separate action.
- If an agent was not invoked, do not mention its domain in actions.
- Do not invent data not present in the expert agent outputs.
"""

# ---------------------------------------------------------------------------
# Supervisor implementation
# ---------------------------------------------------------------------------

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def _route(query: str) -> SupervisorRouting:
    """Call the LLM to produce a routing decision."""
    completion = await _get_client().chat.completions.create(
        model=get_settings().groq_orchestration_model,
        messages=[
            {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    )
    content = completion.choices[0].message.content or ""
    try:
        parsed = extract_json(content)
        return SupervisorRouting(
            requires_waste_agent=bool(parsed.get("requires_waste_agent", False)),
            requires_resource_agent=bool(parsed.get("requires_resource_agent", False)),
            routing_rationale=str(parsed.get("routing_rationale", "No rationale provided.")),
        )
    except (ValueError, KeyError):
        logger.warning("Routing LLM returned non-JSON; defaulting to both agents. Output: %r", content[:200])
        return SupervisorRouting(
            requires_waste_agent=True,
            requires_resource_agent=True,
            routing_rationale="Fallback: routing LLM did not return valid JSON; both agents activated.",
        )


async def _synthesise(
    query: str,
    waste_output: WasteComplianceOutput | None,
    resource_output: ResourcePlanningOutput | None,
) -> tuple[str, list[dict]]:
    """Call the LLM to synthesise expert outputs into a summary + action list."""
    context_parts: list[str] = [f"User query: {query}\n"]

    if waste_output is not None:
        context_parts.append(
            "=== Waste & Compliance Agent Output ===\n"
            + json.dumps(
                {
                    "item_name": waste_output.item_name,
                    "category": waste_output.category.model_dump(),
                    "recycling_sop": waste_output.recycling_sop,
                    "compliance_notes": waste_output.compliance_notes,
                    "regulatory_references": [r.model_dump() for r in waste_output.regulatory_references],
                },
                indent=2,
            )
        )

    if resource_output is not None:
        context_parts.append(
            "=== Resource Planning Agent Output ===\n"
            + json.dumps(
                {
                    "facility_loads": [fl.model_dump() for fl in resource_output.facility_loads],
                    "forecasts": [f.model_dump() for f in resource_output.forecasts],
                    "workload_allocation": resource_output.workload_allocation.model_dump()
                    if resource_output.workload_allocation
                    else None,
                    "planning_notes": resource_output.planning_notes,
                },
                indent=2,
            )
        )

    completion = await _get_client().chat.completions.create(
        model=get_settings().groq_orchestration_model,
        messages=[
            {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(context_parts)},
        ],
    )
    content = completion.choices[0].message.content or ""
    try:
        parsed = extract_json(content)
        return str(parsed.get("synthesis", "")), list(parsed.get("actions", []))
    except (ValueError, KeyError):
        logger.warning("Synthesis LLM returned non-JSON: %r", content[:200])
        return content, []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_supervisor(request: MoERequest) -> MoEResponse:
    """Execute the full MoE pipeline for one request.

    Steps:
      1. Routing: determine which expert agents to activate.
      2. Expert execution: run agents (in parallel if both required).
      3. Synthesis: merge outputs into a coherent response.
      4. Return a fully typed MoEResponse with aggregated trace.
    """
    settings = get_settings()
    trace: list[TraceStep] = []

    # --- Step 1: Routing --------------------------------------------------------
    routing = await _route(request.query)
    trace.append(
        TraceStep(
            tool="supervisor:routing",
            arguments={"query": request.query},
            result=routing.model_dump(),
        )
    )
    logger.info(
        "MoE routing for tenant %s: waste=%s resource=%s | %s",
        request.tenant_id,
        routing.requires_waste_agent,
        routing.requires_resource_agent,
        routing.routing_rationale,
    )

    # Decode image bytes if provided as base64
    image_bytes: bytes | None = None
    if request.image_base64:
        import base64

        image_bytes = base64.b64decode(request.image_base64)

    # --- Step 2: Expert agent execution -----------------------------------------
    waste_output: WasteComplianceOutput | None = None
    resource_output: ResourcePlanningOutput | None = None

    if routing.requires_waste_agent and routing.requires_resource_agent:
        # Run both concurrently
        waste_result, resource_result = await asyncio.gather(
            run_waste_compliance_agent(
                query=request.query,
                image_bytes=image_bytes,
                image_content_type=request.image_content_type,
            ),
            run_resource_planning_agent(
                query=request.query,
                telemetry=request.telemetry,
            ),
        )
        waste_output = waste_result
        resource_output = resource_result
    elif routing.requires_waste_agent:
        waste_output = await run_waste_compliance_agent(
            query=request.query,
            image_bytes=image_bytes,
            image_content_type=request.image_content_type,
        )
    elif routing.requires_resource_agent:
        resource_output = await run_resource_planning_agent(
            query=request.query,
            telemetry=request.telemetry,
        )
    else:
        # No agent activated — routing was ambiguous; default to both
        logger.warning("Routing activated no agents for tenant %s; defaulting to both.", request.tenant_id)
        waste_output, resource_output = await asyncio.gather(
            run_waste_compliance_agent(query=request.query),
            run_resource_planning_agent(query=request.query, telemetry=request.telemetry),
        )

    # Aggregate expert traces
    if waste_output is not None:
        trace.extend(waste_output.trace)
    if resource_output is not None:
        trace.extend(resource_output.trace)

    # --- Step 3: Synthesis -------------------------------------------------------
    synthesis, actions = await _synthesise(request.query, waste_output, resource_output)
    trace.append(
        TraceStep(
            tool="supervisor:synthesis",
            arguments={"query": request.query},
            result={"synthesis": synthesis, "action_count": len(actions)},
        )
    )

    # --- Step 4: Build final response -------------------------------------------
    # Overall confidence: average of available agent confidences
    confidences = [
        c
        for c in [
            waste_output.confidence if waste_output else None,
            resource_output.confidence if resource_output else None,
        ]
        if c is not None
    ]
    overall_confidence = sum(confidences) / len(confidences) if confidences else None

    return MoEResponse(
        routing=routing,
        waste_compliance=waste_output,
        resource_planning=resource_output,
        synthesis=synthesis,
        actions=actions,
        trace=trace,
        confidence=overall_confidence,
        source=settings.groq_orchestration_model,
    )
