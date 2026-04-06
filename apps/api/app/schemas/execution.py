import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ExecutionRequest(BaseModel):
    campaign_id: uuid.UUID
    asset_id: uuid.UUID
    approval_id: uuid.UUID
    channel: str
    provider: str  # sendgrid | hubspot | meta | google


class ExecutionRunRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    asset_id: uuid.UUID | None
    approval_id: uuid.UUID | None
    channel: str
    provider: str
    idempotency_key: str
    status: str
    provider_id: str | None
    result: dict[str, Any]
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
