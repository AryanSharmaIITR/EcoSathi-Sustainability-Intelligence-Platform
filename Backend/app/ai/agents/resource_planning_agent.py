"""Expert Agent 2: Facility Resource Planning & Operations Agent.

Capabilities
------------
1. Multi-facility telemetry ingestion — reads water/energy/waste metrics
   across campus blocks from the TelemetrySnapshot.
2. Resource demand forecasting — calculates water, energy, and labor
   requirements for a described task.
3. Capacity & facility allocation — recommends the optimal building to
   host a processing task based on current load vs. available buffer.
4. Workload tracking — surfaces per-building load and WoW trends.

Implementation
--------------
LangGraph state machine:
  agent → [facility tools] → agent → END

Three tools are available (via facility_tools.py):
  - get_telemetry_summary
  - calculate_resource_requirements
  - recommend_facility_allocation

All tool results are deterministic computations — no model inference is
done in the tools layer.  The model's job is to decide which tools to
call and to synthesise the results into a planning recommendation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict, cast

from groq import AsyncGroq
from langgraph.graph import END, StateGraph

from app.ai.json_utils import extract_json
from app.ai.tools.facility_tools import FACILITY_TOOL_SPECS, call_facility_tool
from app.core.config import get_settings
from app.schemas.agent_io import (
    FacilityLoad,
    ResourceForecast,
    ResourcePlanningOutput,
    TraceStep,
    WorkloadAllocation,
)
from app.schemas.telemetry_schema import TelemetrySnapshot

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 4

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are EcoSathi's Resource & Operations Planning Expert Agent.
You have access to facility telemetry tools that give you real, measured
consumption data for each campus building.

Your responsibilities:
1. Summarise current resource consumption (water, energy) across the campus.
2. Forecast requirements for a described operational task.
3. Recommend the best campus building to assign the task to, based on
   available capacity buffers.

Always call get_telemetry_summary first if telemetry is available.
Then call calculate_resource_requirements and recommend_facility_allocation
as needed.

Respond with ONLY a JSON object:
{
  "facility_loads": [
    {
      "building": "<name>",
      "water_usage_L": <number>,
      "energy_usage_kWh": <number>,
      "waste_scanned_count": <int>,
      "available_buffer_pct": <float 0-100>
    }
  ],
  "forecasts": [
    {
      "resource": "<water|energy|labor>",
      "unit": "<L|kWh|person-hours>",
      "forecasted_requirement": <number>,
      "current_actual": <number or null>,
      "variance_pct": <float or null>,
      "forecast_basis": "<explanation>"
    }
  ],
  "workload_allocation": {
    "recommended_building": "<name>",
    "reason": "<explanation>",
    "alternative_buildings": ["<name>", ...]
  },
  "planning_notes": "<summary of key observations and recommendations>",
  "confidence": <float 0-1>
}

If no telemetry data is available, set facility_loads to [] and note this
in planning_notes. Do not invent consumption numbers.
"""

# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------


class _ResourceAgentState(TypedDict):
    messages: list[dict[str, Any]]
    telemetry: TelemetrySnapshot | None
    trace: list[dict[str, Any]]
    iterations: int


# ---------------------------------------------------------------------------
# LangGraph nodes
# ---------------------------------------------------------------------------

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def _agent_node(state: _ResourceAgentState) -> _ResourceAgentState:
    tool_choice = "auto" if state["iterations"] == 0 else "none"
    completion = await _get_client().chat.completions.create(
        model=get_settings().groq_orchestration_model,
        messages=cast(Any, state["messages"]),
        tools=cast(Any, FACILITY_TOOL_SPECS),
        tool_choice=tool_choice,
    )
    message = completion.choices[0].message
    state["messages"].append(message.model_dump(exclude_none=True))
    state["iterations"] += 1
    return state


async def _tools_node(state: _ResourceAgentState) -> _ResourceAgentState:
    last = state["messages"][-1]
    for tool_call in last.get("tool_calls", []):
        name: str = tool_call["function"]["name"]
        arguments: dict = json.loads(tool_call["function"]["arguments"] or "{}")
        result = await call_facility_tool(name, arguments, telemetry=state.get("telemetry"))
        state["trace"].append({"tool": name, "arguments": arguments, "result": result})
        state["messages"].append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result),
            }
        )
    return state


def _route_after_agent(state: _ResourceAgentState) -> str:
    if state["iterations"] >= _MAX_ITERATIONS:
        return "end"
    last = state["messages"][-1]
    return "tools" if last.get("tool_calls") else "end"


def _build_resource_graph():
    g = StateGraph(_ResourceAgentState)
    g.add_node("agent", _agent_node)
    g.add_node("tools", _tools_node)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile()


_RESOURCE_GRAPH = _build_resource_graph()

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_resource_planning_agent(
    *,
    query: str,
    telemetry: TelemetrySnapshot | None = None,
) -> ResourcePlanningOutput:
    """Run Expert Agent 2 for a resource / operations planning query.

    Args:
        query: User's natural-language question.
        telemetry: Optional current-week telemetry snapshot from /usage.

    Returns:
        A fully typed ``ResourcePlanningOutput`` with forecasts, allocations,
        and the execution trace.
    """
    context_lines = [query]
    if telemetry is not None:
        context_lines.append(
            f"Live telemetry is available for tenant '{telemetry.tenant_id}' "
            f"covering {telemetry.period_start} to {telemetry.period_end}. "
            "Use get_telemetry_summary to read current consumption before making recommendations."
        )
    else:
        context_lines.append(
            "No telemetry snapshot was provided. Work with the information in the query only."
        )

    initial_state: _ResourceAgentState = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": " ".join(context_lines)},
        ],
        "telemetry": telemetry,
        "trace": [],
        "iterations": 0,
    }

    final_state = await _RESOURCE_GRAPH.ainvoke(initial_state)
    last_msg = final_state["messages"][-1]
    content = last_msg.get("content") or ""

    try:
        parsed = extract_json(content)

        facility_loads = [
            FacilityLoad(
                building=fl.get("building", ""),
                water_usage_L=float(fl.get("water_usage_L", 0)),
                energy_usage_kWh=float(fl.get("energy_usage_kWh", 0)),
                waste_scanned_count=int(fl.get("waste_scanned_count", 0)),
                available_buffer_pct=fl.get("available_buffer_pct"),
            )
            for fl in parsed.get("facility_loads", [])
        ]

        forecasts = [
            ResourceForecast(
                resource=f.get("resource", "water"),
                unit=f.get("unit", "L"),
                forecasted_requirement=float(f.get("forecasted_requirement", 0)),
                current_actual=f.get("current_actual"),
                variance_pct=f.get("variance_pct"),
                forecast_basis=str(f.get("forecast_basis", "")),
            )
            for f in parsed.get("forecasts", [])
        ]

        alloc_raw = parsed.get("workload_allocation")
        workload_allocation: WorkloadAllocation | None = None
        if alloc_raw and isinstance(alloc_raw, dict):
            workload_allocation = WorkloadAllocation(
                recommended_building=alloc_raw.get("recommended_building", ""),
                reason=alloc_raw.get("reason", ""),
                alternative_buildings=alloc_raw.get("alternative_buildings", []),
            )

        return ResourcePlanningOutput(
            facility_loads=facility_loads,
            forecasts=forecasts,
            workload_allocation=workload_allocation,
            planning_notes=parsed.get("planning_notes"),
            confidence=float(parsed["confidence"]) if parsed.get("confidence") is not None else None,
            trace=[TraceStep(**t) for t in final_state["trace"]],
        )

    except (ValueError, KeyError, TypeError):
        logger.warning("Resource agent could not parse JSON output: %r", content[:300])
        return ResourcePlanningOutput(
            planning_notes=content if content else "Agent did not produce a structured response.",
            trace=[TraceStep(**t) for t in final_state["trace"]],
        )
