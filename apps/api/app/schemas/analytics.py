import uuid
from typing import Any

from pydantic import BaseModel


class EventIngest(BaseModel):
    campaign_id: uuid.UUID | None = None
    asset_id: uuid.UUID | None = None
    execution_run_id: uuid.UUID | None = None
    event_type: str
    channel: str | None = None
    value: float | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    properties: dict[str, Any] = {}


class ChannelMetrics(BaseModel):
    channel: str
    sends: int = 0
    opens: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0


class AnalyticsSummary(BaseModel):
    campaign_id: uuid.UUID | None = None
    total_sends: int = 0
    total_opens: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    avg_approval_cycle_hours: float = 0.0
    assets_generated: int = 0
    by_channel: list[ChannelMetrics] = []
