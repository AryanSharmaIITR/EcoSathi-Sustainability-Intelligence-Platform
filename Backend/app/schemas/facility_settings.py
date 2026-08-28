import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import APIResponse


class FacilitySettingsRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID

    # Resource caps
    water_daily_limit_L: float | None = None
    water_reserve_buffer_L: float | None = None
    energy_daily_limit_kWh: float | None = None
    energy_peak_load_kW: float | None = None
    solar_generation_kWh: float | None = None

    # Workforce
    headcount_morning: int | None = None
    headcount_evening: int | None = None
    headcount_night: int | None = None

    # Financial
    monthly_budget_INR: float | None = None
    electricity_rate_per_kWh: float | None = None
    water_rate_per_1000L: float | None = None
    labor_cost_per_shift: float | None = None
    hauling_fee_per_ton: float | None = None

    # Revenue
    plastic_yield_per_ton_INR: float | None = None
    compost_yield_per_ton_INR: float | None = None
    metal_yield_per_ton_INR: float | None = None

    updated_at: datetime


class FacilitySettingsUpdate(BaseModel):
    # Resource caps
    water_daily_limit_L: float | None = None
    water_reserve_buffer_L: float | None = None
    energy_daily_limit_kWh: float | None = None
    energy_peak_load_kW: float | None = None
    solar_generation_kWh: float | None = None

    # Workforce
    headcount_morning: int | None = None
    headcount_evening: int | None = None
    headcount_night: int | None = None

    # Financial
    monthly_budget_INR: float | None = None
    electricity_rate_per_kWh: float | None = None
    water_rate_per_1000L: float | None = None
    labor_cost_per_shift: float | None = None
    hauling_fee_per_ton: float | None = None

    # Revenue
    plastic_yield_per_ton_INR: float | None = None
    compost_yield_per_ton_INR: float | None = None
    metal_yield_per_ton_INR: float | None = None


class BuildingZoneRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    max_capacity_kg: float | None = None
    floor_area_sqm: float | None = None
    machinery: list[str] = []
    created_at: datetime
    updated_at: datetime


class BuildingZoneCreate(BaseModel):
    name: str
    max_capacity_kg: float | None = None
    floor_area_sqm: float | None = None
    machinery: list[str] = []


class BuildingZoneUpdate(BaseModel):
    name: str | None = None
    max_capacity_kg: float | None = None
    floor_area_sqm: float | None = None
    machinery: list[str] | None = None
