import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    campaign_id: uuid.UUID
    asset_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    hypothesis: str | None = None
    confidence_threshold: float = Field(default=0.95, ge=0.5, le=0.999)
    auto_promote: bool = True


class ExperimentUpdate(BaseModel):
    name: str | None = None
    hypothesis: str | None = None
    status: str | None = None          # running | paused
    confidence_threshold: float | None = None
    auto_promote: bool | None = None


class ConcludeRequest(BaseModel):
    winner_variant_id: uuid.UUID | None = None  # None = no winner / inconclusive
    promote: bool = True                          # promote winner to is_active


class RecordEventRequest(BaseModel):
    variant_id: uuid.UUID
    event_type: str          # impression | click | conversion
    value: float | None = None


class SetWeightsRequest(BaseModel):
    weights: dict[str, float]  # {variant_id_str: weight}


# ── Responses ─────────────────────────────────────────────────────────────────

class VariantStats(BaseModel):
    variant_id: uuid.UUID
    version: int
    traffic_weight: float
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    ctr: float = 0.0    # click-through rate
    cvr: float = 0.0    # conversion rate
    confidence: float = 0.0  # statistical confidence vs. control (1.0 = control itself)
    is_control: bool = False
    is_winner: bool = False


class ExperimentRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    asset_id: uuid.UUID
    name: str
    hypothesis: str | None
    status: str
    confidence_threshold: float
    auto_promote: bool
    winner_variant_id: uuid.UUID | None
    concluded_at: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExperimentDetailRead(ExperimentRead):
    """ExperimentRead plus live per-variant stats."""
    variant_stats: list[VariantStats] = []
    total_impressions: int = 0
    leading_variant_id: uuid.UUID | None = None
    leading_confidence: float = 0.0
