import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GenerateAssetRequest(BaseModel):
    campaign_id: uuid.UUID
    asset_type: str  # email | social_post | landing_page | ad_copy
    channel: str | None = None
    variant_count: int = Field(default=2, ge=1, le=5)
    brief: str | None = None
    voice_pack_id: uuid.UUID | None = None


class RewriteRequest(BaseModel):
    instruction: str
    # e.g. "make shorter", "add urgency", "remove discount mention"


class ContentVariantRead(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    version: int
    is_active: bool
    body: dict[str, Any]
    quality_score: float | None
    approval_state: str
    model_used: str | None
    banned_phrase_flags: list
    claim_warnings: list
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentAssetRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    asset_type: str
    channel: str | None
    status: str
    voice_pack_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    variants: list[ContentVariantRead] = []

    model_config = {"from_attributes": True}
