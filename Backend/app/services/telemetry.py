import datetime
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.building_zone import BuildingZone
from app.models.usage_record import DailyWeather, UsageRecord
from app.schemas.telemetry_schema import (
    BuildingUsage,
    DailyUsageRow,
    ForecastDataPoint,
    ForecastSeries,
    TelemetrySnapshot,
    UsageSummaryCards,
)

FORECAST_HORIZON_DAYS = 3


def _linear_forecast(values: list[float], horizon: int) -> list[float]:
    """Least-squares linear trend — the 'lightweight regression' the spec
    calls for. Computed fresh from real stored data on every request
    rather than a persisted/versioned model; that's a future increment,
    not something faked here."""
    n = len(values)
    if n == 0:
        return [0.0] * horizon
    if n == 1:
        return [values[0]] * horizon
    xs = range(n)
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom if denom else 0.0
    intercept = mean_y - slope * mean_x
    return [max(0.0, slope * (n + i) + intercept) for i in range(horizon)]


async def _sum_by_day(
    db: AsyncSession, tenant_id: uuid.UUID, resource_type: str, start: datetime.date, end: datetime.date
) -> dict[datetime.date, float]:
    result = await db.execute(
        select(UsageRecord.reading_date, UsageRecord.value).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.resource_type == resource_type,
            UsageRecord.reading_date >= start,
            UsageRecord.reading_date <= end,
        )
    )
    totals: dict[datetime.date, float] = defaultdict(float)
    for reading_date, value in result.all():
        totals[reading_date] += value
    return totals


async def _count_waste_scans(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime.date, end: datetime.date
) -> int:
    start_dt = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.UTC)
    end_dt = datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.UTC)
    result = await db.execute(
        select(func.count()).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.endpoint == "/api/v1/classify",
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
    )
    return result.scalar_one()


def _week_over_week_pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


async def build_telemetry_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    period_start: datetime.date,
    period_end: datetime.date,
) -> TelemetrySnapshot:
    """Builds the exact TelemetrySnapshot the /usage dashboard and the
    resource-planning agent both consume, from real stored UsageRecord /
    DailyWeather / AuditLog rows — no fabricated numbers."""
    period_days = (period_end - period_start).days + 1
    prev_start = period_start - datetime.timedelta(days=period_days)
    prev_end = period_start - datetime.timedelta(days=1)

    water_by_day = await _sum_by_day(db, tenant_id, "water", period_start, period_end)
    energy_by_day = await _sum_by_day(db, tenant_id, "energy", period_start, period_end)
    prev_water_by_day = await _sum_by_day(db, tenant_id, "water", prev_start, prev_end)
    prev_energy_by_day = await _sum_by_day(db, tenant_id, "energy", prev_start, prev_end)

    weather_rows = await db.execute(
        select(DailyWeather.reading_date, DailyWeather.avg_temp_c, DailyWeather.rainfall_mm).where(
            DailyWeather.tenant_id == tenant_id,
            DailyWeather.reading_date >= period_start,
            DailyWeather.reading_date <= period_end,
        )
    )
    weather_by_day = {row[0]: (row[1], row[2]) for row in weather_rows.all()}

    # Fetch authoritative zone names from Settings → Infrastructure
    zone_rows = await db.execute(
        select(BuildingZone.name).where(BuildingZone.tenant_id == tenant_id)
    )
    zone_names: list[str] = [row[0] for row in zone_rows.all()]

    building_rows = await db.execute(
        select(UsageRecord.building, UsageRecord.resource_type, UsageRecord.value).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.reading_date >= period_start,
            UsageRecord.reading_date <= period_end,
        )
    )
    # Seed totals with all known zones (even those with no usage records yet)
    building_totals: dict[str, dict[str, float]] = {
        name: {"water": 0.0, "energy": 0.0} for name in zone_names
    }
    for building, resource_type, value in building_rows.all():
        if building not in building_totals:
            building_totals[building] = {"water": 0.0, "energy": 0.0}
        building_totals[building][resource_type] += value

    waste_count = await _count_waste_scans(db, tenant_id, period_start, period_end)
    prev_waste_count = await _count_waste_scans(db, tenant_id, prev_start, prev_end)

    total_water = sum(water_by_day.values())
    total_energy = sum(energy_by_day.values())

    peak_water_day = max(water_by_day, key=water_by_day.get) if water_by_day else None
    peak_energy_day = max(energy_by_day, key=energy_by_day.get) if energy_by_day else None

    summary = UsageSummaryCards(
        total_water_usage_L=total_water,
        total_energy_usage_kWh=total_energy,
        total_waste_scanned=waste_count,
        avg_daily_water_L=total_water / period_days if period_days else 0.0,
        avg_daily_energy_kWh=total_energy / period_days if period_days else 0.0,
        water_wow_pct=_week_over_week_pct(total_water, sum(prev_water_by_day.values())),
        energy_wow_pct=_week_over_week_pct(total_energy, sum(prev_energy_by_day.values())),
        waste_wow_pct=_week_over_week_pct(waste_count, prev_waste_count),
        peak_water_day=peak_water_day,
        peak_water_day_L=water_by_day.get(peak_water_day) if peak_water_day else None,
        peak_energy_day=peak_energy_day,
        peak_energy_day_kWh=energy_by_day.get(peak_energy_day) if peak_energy_day else None,
    )

    ordered_days = [period_start + datetime.timedelta(days=i) for i in range(period_days)]
    daily_rows = [
        DailyUsageRow(
            date=day,
            water_usage_L=water_by_day.get(day, 0.0),
            energy_usage_kWh=energy_by_day.get(day, 0.0),
            avg_temp_C=weather_by_day.get(day, (0.0, 0.0))[0],
            rainfall_mm=weather_by_day.get(day, (0.0, 0.0))[1],
        )
        for day in ordered_days
    ]

    forecast_series = []
    for resource, unit, by_day in (("water", "L", water_by_day), ("energy", "kWh", energy_by_day)):
        actuals = [by_day.get(d, 0.0) for d in ordered_days]
        forecast_values = _linear_forecast(actuals, FORECAST_HORIZON_DAYS)
        points = [ForecastDataPoint(date=d, actual=by_day.get(d, 0.0)) for d in ordered_days]
        points.extend(
            ForecastDataPoint(date=period_end + datetime.timedelta(days=i + 1), forecast=value)
            for i, value in enumerate(forecast_values)
        )
        insight = None
        if actuals and actuals[-1]:
            trend_pct = round((forecast_values[-1] - actuals[-1]) / actuals[-1] * 100, 1)
            direction = "decrease" if trend_pct < 0 else "increase"
            insight = (
                f"{resource.capitalize()} usage is trending to {direction} by about "
                f"{abs(trend_pct)}% over the next {FORECAST_HORIZON_DAYS} days, based on a "
                "linear fit of the current period's data."
            )
        forecast_series.append(
            ForecastSeries(resource=resource, unit=unit, data_points=points, forecast_insight=insight)
        )

    buildings = [
        BuildingUsage(
            building=building,
            water_usage_L=totals["water"],
            energy_usage_kWh=totals["energy"],
            waste_scanned_count=0,  # not derivable yet — classify calls aren't tagged by building
        )
        for building, totals in building_totals.items()
    ]

    return TelemetrySnapshot(
        tenant_id=str(tenant_id),
        period_start=period_start,
        period_end=period_end,
        summary=summary,
        daily_rows=daily_rows,
        forecast_series=forecast_series,
        buildings=buildings,
    )
