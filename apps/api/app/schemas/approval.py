import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ApprovalCreate(BaseModel):
    campaign_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    approval_type: str = "content"  # content | publish | spend | outbound
    due_date: str | None = None
    release_target: str | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected", "changes_requested"]
    comment: str | None = None


class ApprovalCommentCreate(BaseModel):
    body: str


class ApprovalCommentRead(BaseModel):
    id: uuid.UUID
    approval_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    asset_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    approval_type: str
    status: str
    requester_id: uuid.UUID
    approver_id: uuid.UUID | None
    due_date: str | None
    policy_check_results: dict[str, Any]
    release_target: str | None
    created_at: datetime
    updated_at: datetime
    comments: list[ApprovalCommentRead] = []

    model_config = {"from_attributes": True}
