"""alert_engine.py — Evaluates facility constraints against live telemetry
and persists AlertIncident rows when thresholds are exceeded.

Called from POST /api/v1/alerts/evaluate. Deduplicates by trigger_type
so re-running does not create duplicate active alerts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_incident import AlertIncident

if TYPE_CHECKING:
    from app.models.facility_settings import FacilitySettings
    from app.schemas.telemetry_schema import TelemetrySnapshot


_WATER_TRIGGER = "water_deficit"
_ENERGY_TRIGGER = "energy_overload"
_ROI_TRIGGER = "roi_negative"
_WORKFORCE_TRIGGER = "workforce_deficit"


async def _active_trigger_types(db: AsyncSession, tenant_id: uuid.UUID) -> set[str]:
    """Return trigger_types that already have an active alert for this tenant."""
    result = await db.execute(
        select(AlertIncident.trigger_type).where(
            AlertIncident.tenant_id == tenant_id,
            AlertIncident.status == "active",
        )
    )
    return {row for row in result.scalars().all()}


def _pct_over(actual: float, limit: float) -> float:
    return ((actual - limit) / limit) * 100.0


async def evaluate_constraints(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    snapshot: "TelemetrySnapshot",
    settings: "FacilitySettings",
) -> list[AlertIncident]:
    """Evaluate telemetry snapshot against facility settings and persist
    new AlertIncident rows.  Returns the newly created incidents.

    Skips any trigger_type that already has an active alert (dedup).
    """
    existing = await _active_trigger_types(db, tenant_id)
    new_alerts: list[AlertIncident] = []
    now = datetime.now(UTC)

    summary = snapshot.summary
    from datetime import date as _date

    period_start: _date = (
        _date.fromisoformat(snapshot.period_start)
        if isinstance(snapshot.period_start, str)
        else snapshot.period_start
    )
    period_end: _date = (
        _date.fromisoformat(snapshot.period_end)
        if isinstance(snapshot.period_end, str)
        else snapshot.period_end
    )
    period_days = max(1, (period_end - period_start).days)

    # ── 1. Water deficit ────────────────────────────────────────────────────
    if (
        _WATER_TRIGGER not in existing
        and settings.water_daily_limit_L is not None
        and summary.total_water_usage_L is not None
    ):
        avg_daily = summary.total_water_usage_L / period_days
        if avg_daily > settings.water_daily_limit_L:
            pct = _pct_over(avg_daily, settings.water_daily_limit_L)
            alert = AlertIncident(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                severity="critical",
                trigger_type=_WATER_TRIGGER,
                title="Water Usage Exceeds Daily Cap",
                message=(
                    f"Avg daily water usage at {avg_daily:,.0f} L exceeds "
                    f"{settings.water_daily_limit_L:,.0f} L cap by +{pct:.1f}%."
                ),
                metric_actual=round(avg_daily, 2),
                metric_limit=settings.water_daily_limit_L,
                metric_unit="L/day",
                ai_recommendation=(
                    "Review irrigation schedules and leak detection logs. "
                    "Consider installing flow restrictors in non-critical zones."
                ),
                status="active",
                triggered_at=now,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 2. Energy overload ──────────────────────────────────────────────────
    if (
        _ENERGY_TRIGGER not in existing
        and settings.energy_daily_limit_kWh is not None
        and summary.total_energy_usage_kWh is not None
    ):
        avg_daily_kwh = summary.total_energy_usage_kWh / period_days
        if avg_daily_kwh > settings.energy_daily_limit_kWh:
            pct = _pct_over(avg_daily_kwh, settings.energy_daily_limit_kWh)
            alert = AlertIncident(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                severity="high",
                trigger_type=_ENERGY_TRIGGER,
                title="Energy Consumption Exceeds Daily Limit",
                message=(
                    f"Avg daily energy at {avg_daily_kwh:,.1f} kWh exceeds "
                    f"{settings.energy_daily_limit_kWh:,.1f} kWh limit by +{pct:.1f}%."
                ),
                metric_actual=round(avg_daily_kwh, 2),
                metric_limit=settings.energy_daily_limit_kWh,
                metric_unit="kWh/day",
                ai_recommendation=(
                    "Audit HVAC and processing equipment runtime. "
                    "Shift non-essential loads to off-peak hours."
                ),
                status="active",
                triggered_at=now,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 3. ROI negative ────────────────────────────────────────────────────
    # Only meaningful when rates AND usage data are available; skip if the
    # telemetry period has zero consumption (avoids false-positive on new tenants).
    if (
        _ROI_TRIGGER not in existing
        and settings.electricity_rate_per_kWh is not None
        and (summary.total_energy_usage_kWh > 0 or summary.total_water_usage_L > 0)
    ):
        # Estimated revenue from sorted waste (use scan counts as proxy tonnage)
        total_scans = summary.total_waste_scanned or 0
        # Assume each scan ≈ 10 kg => convert to tons
        approx_tons = total_scans * 0.01

        plastic_rev = (settings.plastic_yield_per_ton_INR or 0) * approx_tons * 0.4
        compost_rev = (settings.compost_yield_per_ton_INR or 0) * approx_tons * 0.35
        metal_rev = (settings.metal_yield_per_ton_INR or 0) * approx_tons * 0.25
        projected_revenue = plastic_rev + compost_rev + metal_rev

        energy_cost = summary.total_energy_usage_kWh * settings.electricity_rate_per_kWh
        water_cost = (
            summary.total_water_usage_L / 1000.0 * (settings.water_rate_per_1000L or 0)
        )
        shift_count = 3  # morning + evening + night
        labor_cost = (settings.labor_cost_per_shift or 0) * shift_count * period_days
        haul_cost = (settings.hauling_fee_per_ton or 0) * approx_tons
        operational_cost = energy_cost + water_cost + labor_cost + haul_cost

        if projected_revenue - operational_cost < 0:
            deficit = operational_cost - projected_revenue
            alert = AlertIncident(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                severity="warning",
                trigger_type=_ROI_TRIGGER,
                title="Projected ROI Is Negative",
                message=(
                    f"Estimated revenue ₹{projected_revenue:,.0f} is below "
                    f"operational cost ₹{operational_cost:,.0f} "
                    f"(deficit ₹{deficit:,.0f} for this period)."
                ),
                metric_actual=round(projected_revenue, 2),
                metric_limit=round(operational_cost, 2),
                metric_unit="INR",
                ai_recommendation=(
                    "Review commodity pricing and increase recyclable material yield. "
                    "Target high-value streams (metal, plastic) to improve margins."
                ),
                status="active",
                triggered_at=now,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 4. Workforce deficit ────────────────────────────────────────────────
    # Only fire when headcount has been explicitly configured as 0.
    # NULL means "not set yet" — triggering on unset fields would create
    # noise for every new tenant before they configure their settings.
    if _WORKFORCE_TRIGGER not in existing:
        zero_shifts = []
        if settings.headcount_morning is not None and settings.headcount_morning == 0:
            zero_shifts.append("Morning")
        if settings.headcount_evening is not None and settings.headcount_evening == 0:
            zero_shifts.append("Evening")
        if settings.headcount_night is not None and settings.headcount_night == 0:
            zero_shifts.append("Night")

        if zero_shifts:
            shifts_str = ", ".join(zero_shifts)
            alert = AlertIncident(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                severity="warning",
                trigger_type=_WORKFORCE_TRIGGER,
                title="Unstaffed Shift Detected",
                message=(
                    f"{shifts_str} shift(s) have zero headcount assigned. "
                    "Sorting operations may be unmonitored."
                ),
                metric_actual=0,
                metric_limit=1,
                metric_unit="headcount",
                ai_recommendation=(
                    "Assign at least one operator per active shift. "
                    "Consider flexible rostering during low-throughput periods."
                ),
                status="active",
                triggered_at=now,
            )
            db.add(alert)
            new_alerts.append(alert)

    if new_alerts:
        await db.commit()
        for a in new_alerts:
            await db.refresh(a)

    return new_alerts
