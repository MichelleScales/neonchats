import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VoicePackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tone: dict[str, Any] = Field(default_factory=dict)
    vocabulary: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    claims_policy: dict[str, Any] = Field(default_factory=dict)
    style_summary: str | None = None


class VoicePackUpdate(BaseModel):
    name: str | None = None
    tone: dict[str, Any] | None = None
    vocabulary: list[str] | None = None
    banned_phrases: list[str] | None = None
    claims_policy: dict[str, Any] | None = None
    style_summary: str | None = None
    is_active: bool | None = None


class VoicePackRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool
    version: int
    tone: dict[str, Any]
    vocabulary: list
    banned_phrases: list
    claims_policy: dict[str, Any]
    style_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CanonDocumentCreate(BaseModel):
    title: str
    source_type: str  # upload | website | manual
    source_url: str | None = None
    content: str | None = None
    channel: str | None = None


class CanonDocumentRead(CanonDocumentCreate):
    id: uuid.UUID
    voice_pack_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestRequest(BaseModel):
    source_type: str  # upload | website
    source_url: str | None = None
    content: str | None = None
    channel: str | None = None
