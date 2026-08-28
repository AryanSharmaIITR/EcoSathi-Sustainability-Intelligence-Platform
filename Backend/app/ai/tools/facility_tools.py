"""Facility tools — deterministic calculations for energy, water, and labor
resource planning.

These tools are invoked by Expert Agent 2 (Resource & Ops Planning) via
the standard tool-calling interface.  All computations are fully deterministic
and auditable — no model inference happens here.

Calculation methods are conservative estimates used as planning baselines;
the agent is responsible for presenting them with appropriate uncertainty.
"""

from __future__ import annotations

from typing import Any

from app.schemas.telemetry_schema import BuildingUsage, TelemetrySnapshot

# ---------------------------------------------------------------------------
# Tool specs
# ---------------------------------------------------------------------------

FACILITY_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculate_resource_requirements",
            "description": (
                "Calculate the estimated water (L), energy (kWh), and labor (person-hours) "
                "required for a described operational task at the facility. "
                "Returns a breakdown per resource type with the calculation basis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Short description of the task, e.g. 'compost 500 kg organic waste'.",
                    },
                    "waste_weight_kg": {
                        "type": "number",
                        "description": "Weight of waste to process in kilograms (if applicable).",
                    },
                    "duration_days": {
                        "type": "integer",
                        "description": "Number of operating days the task spans.",
                        "minimum": 1,
                    },
                    "num_workers": {
                        "type": "integer",
                        "description": "Estimated number of workers involved.",
                        "minimum": 1,
                    },
                },
                "required": ["task_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_facility_allocation",
            "description": (
                "Given the current telemetry snapshot and a task workload estimate, "
                "recommend the best campus building / facility block to host the task. "
                "Ranks buildings by available capacity buffer. "
                "Requires telemetry context to be available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "required_water_L": {
                        "type": "number",
                        "description": "Additional water demand of the task in litres.",
                    },
                    "required_energy_kWh": {
                        "type": "number",
                        "description": "Additional energy demand of the task in kWh.",
                    },
                    "task_description": {"type": "string"},
                },
                "required": ["task_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_telemetry_summary",
            "description": (
                "Summarise the current week's facility resource consumption from the "
                "telemetry snapshot: total water/energy, per-building breakdown, "
                "week-over-week trends, and any buildings near capacity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_filter": {
                        "type": "string",
                        "enum": ["water", "energy", "both"],
                        "description": "Which resource to summarise.",
                    }
                },
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Per-unit consumption benchmarks (conservative industry averages for India)
# ---------------------------------------------------------------------------

# Water consumed per kg of organic waste composted (L/kg)
_WATER_PER_KG_COMPOST_L = 2.5
# Energy consumed per kg of general waste processed (kWh/kg)
_ENERGY_PER_KG_WASTE_KWH = 0.15
# Person-hours per tonne of waste manually sorted
_LABOR_PER_TONNE_SORT_HRS = 8.0
# Baseline daily water usage for a worker on-site (L/person/day)
_WORKER_DAILY_WATER_L = 50.0
# Baseline daily energy usage for a worker station (kWh/person/day)
_WORKER_DAILY_ENERGY_KWH = 5.0


# ---------------------------------------------------------------------------
# Tool call implementations
# ---------------------------------------------------------------------------


def _calculate_resource_requirements(arguments: dict) -> dict:
    waste_kg: float = float(arguments.get("waste_weight_kg") or 0.0)
    duration_days: int = max(1, int(arguments.get("duration_days") or 1))
    num_workers: int = max(1, int(arguments.get("num_workers") or 2))
    task = str(arguments.get("task_description", ""))

    water_L = (waste_kg * _WATER_PER_KG_COMPOST_L) + (num_workers * _WORKER_DAILY_WATER_L * duration_days)
    energy_kWh = (waste_kg * _ENERGY_PER_KG_WASTE_KWH) + (num_workers * _WORKER_DAILY_ENERGY_KWH * duration_days)
    labor_hours = (waste_kg / 1000.0) * _LABOR_PER_TONNE_SORT_HRS * duration_days

    return {
        "task": task,
        "duration_days": duration_days,
        "num_workers": num_workers,
        "waste_weight_kg": waste_kg,
        "estimates": {
            "water_L": round(water_L, 1),
            "energy_kWh": round(energy_kWh, 2),
            "labor_person_hours": round(labor_hours, 1),
        },
        "basis": (
            f"Water: {waste_kg} kg × {_WATER_PER_KG_COMPOST_L} L/kg + "
            f"{num_workers} workers × {_WORKER_DAILY_WATER_L} L/day × {duration_days} days. "
            f"Energy: {waste_kg} kg × {_ENERGY_PER_KG_WASTE_KWH} kWh/kg + "
            f"{num_workers} workers × {_WORKER_DAILY_ENERGY_KWH} kWh/day × {duration_days} days. "
            f"Labor: {waste_kg / 1000:.2f} tonnes × {_LABOR_PER_TONNE_SORT_HRS} person-hrs/tonne × {duration_days} days."
        ),
    }


def _recommend_facility_allocation(arguments: dict, telemetry: TelemetrySnapshot | None) -> dict:
    task = str(arguments.get("task_description", ""))
    extra_water = float(arguments.get("required_water_L") or 0.0)
    extra_energy = float(arguments.get("required_energy_kWh") or 0.0)

    if telemetry is None or not telemetry.buildings:
        return {
            "available": False,
            "message": "No telemetry data available — cannot make a data-driven allocation recommendation.",
            "task": task,
        }

    buildings: list[BuildingUsage] = telemetry.buildings
    # Compute a simple "load score" as fraction of max building usage
    max_water = max((b.water_usage_L for b in buildings), default=1.0)
    max_energy = max((b.energy_usage_kWh for b in buildings), default=1.0)

    ranked: list[dict] = []
    for b in buildings:
        water_load_pct = (b.water_usage_L / max_water) * 100
        energy_load_pct = (b.energy_usage_kWh / max_energy) * 100
        composite_load = (water_load_pct + energy_load_pct) / 2
        buffer_pct = round(100 - composite_load, 1)
        ranked.append(
            {
                "building": b.building,
                "current_water_L": b.water_usage_L,
                "current_energy_kWh": b.energy_usage_kWh,
                "load_pct": round(composite_load, 1),
                "available_buffer_pct": buffer_pct,
                "projected_water_L_after_task": round(b.water_usage_L + extra_water, 1),
                "projected_energy_kWh_after_task": round(b.energy_usage_kWh + extra_energy, 2),
            }
        )

    # Sort by most available buffer (lowest current load)
    ranked.sort(key=lambda x: x["available_buffer_pct"], reverse=True)

    return {
        "task": task,
        "recommended_building": ranked[0]["building"],
        "recommendation_reason": (
            f"{ranked[0]['building']} has the highest available capacity buffer "
            f"({ranked[0]['available_buffer_pct']}%) among all campus buildings."
        ),
        "all_buildings_ranked": ranked,
        "extra_demand": {"water_L": extra_water, "energy_kWh": extra_energy},
    }


def _get_telemetry_summary(arguments: dict, telemetry: TelemetrySnapshot | None) -> dict:
    resource_filter = arguments.get("resource_filter", "both")

    if telemetry is None:
        return {
            "available": False,
            "message": "No telemetry snapshot provided — usage data unavailable.",
        }

    s = telemetry.summary
    result: dict = {
        "period": f"{telemetry.period_start} to {telemetry.period_end}",
        "tenant_id": telemetry.tenant_id,
    }

    if resource_filter in ("water", "both"):
        result["water"] = {
            "total_L": s.total_water_usage_L,
            "avg_daily_L": s.avg_daily_water_L,
            "wow_change_pct": s.water_wow_pct,
            "peak_day": str(s.peak_water_day) if s.peak_water_day else None,
            "peak_day_L": s.peak_water_day_L,
        }

    if resource_filter in ("energy", "both"):
        result["energy"] = {
            "total_kWh": s.total_energy_usage_kWh,
            "avg_daily_kWh": s.avg_daily_energy_kWh,
            "wow_change_pct": s.energy_wow_pct,
            "peak_day": str(s.peak_energy_day) if s.peak_energy_day else None,
            "peak_day_kWh": s.peak_energy_day_kWh,
        }

    if telemetry.buildings:
        result["buildings"] = [
            {"building": b.building, "water_L": b.water_usage_L, "energy_kWh": b.energy_usage_kWh}
            for b in telemetry.buildings
        ]

    return result


# ---------------------------------------------------------------------------
# Public dispatch function
# ---------------------------------------------------------------------------


async def call_facility_tool(
    name: str,
    arguments: dict,
    *,
    telemetry: TelemetrySnapshot | None,
) -> dict:
    """Execute a facility tool call by name.  Every result is logged by the
    caller (see central_supervisor / orchestrator) — this function is the
    deterministic computation layer only.
    """
    if name == "calculate_resource_requirements":
        return _calculate_resource_requirements(arguments)
    if name == "recommend_facility_allocation":
        return _recommend_facility_allocation(arguments, telemetry)
    if name == "get_telemetry_summary":
        return _get_telemetry_summary(arguments, telemetry)
    return {"error": f"Unknown facility tool: {name}"}
