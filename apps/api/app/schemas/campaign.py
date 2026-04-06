import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CampaignChannelCreate(BaseModel):
    channel: str
    config: dict[str, Any] = Field(default_factory=dict)


class CampaignChannelRead(CampaignChannelCreate):
    id: uuid.UUID
    campaign_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    goal: str | None = None
    audience_summary: str | None = None
    channels: list[str] = Field(default_factory=list)
    offer: dict[str, Any] = Field(default_factory=dict)
    brief: str | None = None
    compliance_notes: str | None = None
    launch_at: str | None = None
    budget: float | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    audience_summary: str | None = None
    offer: dict[str, Any] | None = None
    brief: str | None = None
    compliance_notes: str | None = None
    launch_at: str | None = None
    budget: float | None = None
    status: str | None = None


class CampaignRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: str
    goal: str | None
    audience_summary: str | None
    offer: dict[str, Any]
    brief: str | None
    compliance_notes: str | None
    launch_at: str | None
    budget: float | None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None
    channels: list[CampaignChannelRead] = []

    model_config = {"from_attributes": True}


class CampaignList(BaseModel):
    items: list[CampaignRead]
    total: int
    page: int
    page_size: int
