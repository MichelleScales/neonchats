import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.approval import Approval, ApprovalComment
from app.models.content import ContentAsset, ContentVariant
from app.routers.deps import DB, CurrentUser
from app.schemas.approval import (
    ApprovalCommentCreate, ApprovalCommentRead,
    ApprovalCreate, ApprovalDecision, ApprovalRead,
)
from app.services.audit import log_action
from app.services.policy import run_policy_checks

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def create_approval(payload: ApprovalCreate, db: DB, user: CurrentUser):
    # Run policy checks on active variant body
    policy_results = {}
    if payload.variant_id:
        vr = await db.execute(select(ContentVariant).where(ContentVariant.id == payload.variant_id))
        variant = vr.scalar_one_or_none()
        if variant:
            body_text = " ".join(str(v) for v in variant.body.values() if v)
            policy_results = run_policy_checks(body_text, banned_phrases=[], claims_policy={})

    approval = Approval(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_id,
        variant_id=payload.variant_id,
        approval_type=payload.approval_type,
        requester_id=user.user_id,
        due_date=payload.due_date,
        release_target=payload.release_target,
        policy_check_results=policy_results,
    )
    db.add(approval)
    await db.flush()

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="approval.created",
        resource_type="approval",
        resource_id=str(approval.id),
    )
    await db.refresh(approval, ["comments"])
    return approval


@router.get("", response_model=list[ApprovalRead])
async def list_approvals(
    db: DB,
    user: CurrentUser,
    status: str | None = None,
    approval_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = select(Approval).where(Approval.tenant_id == user.tenant_id)
    if status:
        q = q.where(Approval.status == status)
    if approval_type:
        q = q.where(Approval.approval_type == approval_type)
    q = q.options(selectinload(Approval.comments)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/{approval_id}/decision", response_model=ApprovalRead)
async def make_decision(approval_id: uuid.UUID, payload: ApprovalDecision, db: DB, user: CurrentUser):
    if "approver" not in user.roles and "workspace_admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Only approvers can make decisions")

    result = await db.execute(
        select(Approval)
        .where(Approval.id == approval_id, Approval.tenant_id == user.tenant_id)
        .options(selectinload(Approval.comments))
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")

    approval.status = payload.decision
    approval.approver_id = user.user_id

    # Update variant approval state
    if approval.variant_id:
        vr = await db.execute(select(ContentVariant).where(ContentVariant.id == approval.variant_id))
        variant = vr.scalar_one_or_none()
        if variant:
            variant.approval_state = payload.decision

    if payload.comment:
        comment = ApprovalComment(
            tenant_id=user.tenant_id,
            created_by=user.user_id,
            approval_id=approval.id,
            author_id=user.user_id,
            body=payload.comment,
        )
        db.add(comment)

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action=f"approval.{payload.decision}",
        resource_type="approval",
        resource_id=str(approval.id),
        summary=f"Decision: {payload.decision}. {payload.comment or ''}",
    )
    await db.refresh(approval, ["comments"])
    return approval


@router.post("/{approval_id}/comments", response_model=ApprovalCommentRead)
async def add_comment(approval_id: uuid.UUID, payload: ApprovalCommentCreate, db: DB, user: CurrentUser):
    result = await db.execute(
        select(Approval).where(Approval.id == approval_id, Approval.tenant_id == user.tenant_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Approval not found")

    comment = ApprovalComment(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        approval_id=approval_id,
        author_id=user.user_id,
        body=payload.body,
    )
    db.add(comment)
    await db.flush()
    return comment
