"""add facility_settings, building_zones, alert_incidents tables

Revision ID: 0003c1d2e3f4
Revises: aae736049e9f
Create Date: 2026-08-27 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "aae736049e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add facility_settings, building_zones, and alert_incidents tables."""
    op.create_table(
        "facility_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("water_daily_limit_L", sa.Float(), nullable=True),
        sa.Column("water_reserve_buffer_L", sa.Float(), nullable=True),
        sa.Column("energy_daily_limit_kWh", sa.Float(), nullable=True),
        sa.Column("energy_peak_load_kW", sa.Float(), nullable=True),
        sa.Column("solar_generation_kWh", sa.Float(), nullable=True),
        sa.Column("headcount_morning", sa.Integer(), nullable=True),
        sa.Column("headcount_evening", sa.Integer(), nullable=True),
        sa.Column("headcount_night", sa.Integer(), nullable=True),
        sa.Column("monthly_budget_INR", sa.Float(), nullable=True),
        sa.Column("electricity_rate_per_kWh", sa.Float(), nullable=True),
        sa.Column("water_rate_per_1000L", sa.Float(), nullable=True),
        sa.Column("labor_cost_per_shift", sa.Float(), nullable=True),
        sa.Column("hauling_fee_per_ton", sa.Float(), nullable=True),
        sa.Column("plastic_yield_per_ton_INR", sa.Float(), nullable=True),
        sa.Column("compost_yield_per_ton_INR", sa.Float(), nullable=True),
        sa.Column("metal_yield_per_ton_INR", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_facility_settings_tenant_id"),
        "facility_settings",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "building_zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("max_capacity_kg", sa.Float(), nullable=True),
        sa.Column("floor_area_sqm", sa.Float(), nullable=True),
        sa.Column("machinery", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_building_zones_tenant_id"),
        "building_zones",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "alert_incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("metric_actual", sa.Float(), nullable=True),
        sa.Column("metric_limit", sa.Float(), nullable=True),
        sa.Column("metric_unit", sa.String(length=50), nullable=True),
        sa.Column("building", sa.String(length=255), nullable=True),
        sa.Column("ai_recommendation", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_alert_incidents_tenant_id"),
        "alert_incidents",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop facility_settings, building_zones, and alert_incidents tables."""
    op.drop_index(op.f("ix_alert_incidents_tenant_id"), table_name="alert_incidents")
    op.drop_table("alert_incidents")
    op.drop_index(op.f("ix_building_zones_tenant_id"), table_name="building_zones")
    op.drop_table("building_zones")
    op.drop_index(op.f("ix_facility_settings_tenant_id"), table_name="facility_settings")
    op.drop_table("facility_settings")
