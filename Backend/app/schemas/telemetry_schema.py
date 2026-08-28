"""Telemetry schemas mirroring the /usage dashboard.

These models are the canonical representation of facility resource-consumption
data that the Usage dashboard displays and that Expert Agent 2 (Resource &
Ops Planning) ingests for forecasting and workload allocation.

Field names and units map 1-to-1 with the dashboard UI:
  - Water Usage (L), Energy Usage (kWh), Waste Scanned (items)
  - Daily Usage Table: date, water_usage_L, energy_usage_kWh, avg_temp_C, rainfall_mm
  - Usage by Building breakdown
  - Forecast vs. Actual series
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Summary cards (top row of the dashboard)
# ---------------------------------------------------------------------------


class UsageSummaryCards(BaseModel):
    """Aggregate totals shown in the four summary cards at the top of /usage."""

    total_water_usage_L: float = Field(description="Total water usage in litres for the period.")
    total_energy_usage_kWh: float = Field(description="Total energy usage in kWh for the period.")
    total_waste_scanned: int = Field(description="Number of waste items scanned in the period.")
    avg_daily_water_L: float = Field(description="Average daily water usage in litres.")
    avg_daily_energy_kWh: float = Field(description="Average daily energy usage in kWh.")

    # Week-over-week change percentages (negative = reduction, positive = increase)
    water_wow_pct: float | None = Field(
        default=None,
        description="Water usage change vs. last week (%). Negative means decreased.",
    )
    energy_wow_pct: float | None = Field(default=None, description="Energy WoW % change.")
    waste_wow_pct: float | None = Field(default=None, description="Waste scanned WoW % change.")

    peak_water_day: datetime.date | None = None
    peak_water_day_L: float | None = None
    peak_energy_day: datetime.date | None = None
    peak_energy_day_kWh: float | None = None


# ---------------------------------------------------------------------------
# Daily usage row (the table in the bottom-right of the dashboard)
# ---------------------------------------------------------------------------


class DailyUsageRow(BaseModel):
    """One row of the Daily Usage Table from the /usage dashboard."""

    date: datetime.date
    water_usage_L: float
    energy_usage_kWh: float
    avg_temp_C: float = Field(description="Average temperature in °C (weather correlation).")
    rainfall_mm: float = Field(description="Rainfall in mm (weather correlation).")


# ---------------------------------------------------------------------------
# Forecast series (actual vs. predicted line chart)
# ---------------------------------------------------------------------------


class ForecastDataPoint(BaseModel):
    """Single data-point on the forecast/actual chart."""

    date: datetime.date
    actual: float | None = Field(default=None, description="Measured actual value.")
    forecast: float | None = Field(default=None, description="Model-predicted value.")


class ForecastSeries(BaseModel):
    """Forecast-vs-actual series for one resource type."""

    resource: str = Field(description="'water' or 'energy'.")
    unit: str = Field(description="'L' for water, 'kWh' for energy.")
    data_points: list[ForecastDataPoint] = Field(default_factory=list)
    forecast_insight: str | None = Field(
        default=None,
        description="Human-readable forecast insight shown in the sidebar (e.g. 'Usage expected to decrease by 5-8%').",
    )


# ---------------------------------------------------------------------------
# Per-building breakdown (bar chart on bottom-left)
# ---------------------------------------------------------------------------


class BuildingUsage(BaseModel):
    """Resource usage attributed to one campus building."""

    building: str = Field(description="Building name, e.g. 'Block A', 'Hostel', 'Admin Building'.")
    water_usage_L: float = Field(default=0.0)
    energy_usage_kWh: float = Field(default=0.0)
    waste_scanned_count: int = Field(default=0)


# ---------------------------------------------------------------------------
# Top-level snapshot — this is what the Resource Planning Agent ingests
# ---------------------------------------------------------------------------


class TelemetrySnapshot(BaseModel):
    """Full telemetry context for one tenant's /usage dashboard view.

    Populated from the API and passed directly to Expert Agent 2 so that
    forecasting and workload allocation decisions are grounded in real data
    rather than hallucinated numbers.
    """

    tenant_id: str
    period_start: datetime.date
    period_end: datetime.date
    summary: UsageSummaryCards
    daily_rows: list[DailyUsageRow] = Field(default_factory=list)
    forecast_series: list[ForecastSeries] = Field(default_factory=list)
    buildings: list[BuildingUsage] = Field(default_factory=list)
