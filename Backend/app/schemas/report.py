import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.base import APIResponse

ReportType = Literal["sustainability", "water", "energy", "waste", "emissions"]


class GeneratedReportRead(APIResponse):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_type: ReportType
    period_start: datetime.date
    period_end: datetime.date
    generated_by: str
    download_count: int
    created_at: datetime.datetime


class GenerateReportRequest(BaseModel):
    report_type: ReportType
    period_start: datetime.date
    period_end: datetime.date


class ReportsStats(APIResponse):
    reports_generated: int
    total_downloads: int
    data_points_analyzed: int
    insights_generated: int
    co2_avoided_kg: float


class ReportsListResponse(APIResponse):
    stats: ReportsStats
    items: list[GeneratedReportRead]
