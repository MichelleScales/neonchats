import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CredentialUpsert(BaseModel):
    provider: str
    label: str | None = None
    credentials: dict[str, Any] = Field(..., description="Provider-specific credential fields")


class CredentialRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    provider: str
    label: str | None
    is_active: bool
    last_verified_at: datetime | None
    created_at: datetime
    # Never return the raw credentials dict — return redacted keys only
    credential_keys: list[str] = []

    model_config = {"from_attributes": True}


class ConnectorJobRead(BaseModel):
    id: uuid.UUID
    provider: str
    channel: str
    status: str
    provider_job_id: str | None
    error_message: str | None
    attempt: int
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    execution_run_id: uuid.UUID | None
    campaign_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class GatewayStatusItem(BaseModel):
    provider: str
    connected: bool
    detail: dict[str, Any] = {}
    error: str | None = None
    has_credentials: bool = False
