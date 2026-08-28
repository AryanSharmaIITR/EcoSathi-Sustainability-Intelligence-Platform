import datetime
import uuid

from app.schemas.base import APIResponse


class WasteScanItem(APIResponse):
    id: uuid.UUID
    item_name: str
    category: str
    disposal_instructions: str
    confidence: float | None
    source: str | None
    input_ref: str
    scanned_at: datetime.datetime


class WasteScanStats(APIResponse):
    total_scans: int
    recyclable_count: int
    compostable_count: int
    non_recyclable_count: int
    avg_confidence: float | None
    total_scans_wow_pct: float | None


class WasteScanHistoryResponse(APIResponse):
    stats: WasteScanStats
    items: list[WasteScanItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
