import hashlib
import time
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.models.analytics import AnalyticsEvent
from app.models.approval import Approval
from app.models.campaign import Campaign, CampaignChannel
from app.models.content import ContentAsset, ContentVariant
from app.models.execution import ExecutionRun
from app.routers.deps import DB, CurrentUser
from app.schemas.execution import ExecutionRequest, ExecutionRunRead
from app.services.audit import log_action
from app.services.execution import make_idempotency_key, resolve_email_recipients
from app.services import gateway

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("/campaign/{campaign_id}", response_model=list[ExecutionRunRead])
async def list_campaign_executions(campaign_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ExecutionRun)
        .where(ExecutionRun.campaign_id == campaign_id, ExecutionRun.tenant_id == user.tenant_id)
        .order_by(ExecutionRun.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{run_id}/retry", response_model=ExecutionRunRead, status_code=status.HTTP_201_CREATED)
async def retry_execution(run_id: uuid.UUID, db: DB, user: CurrentUser):
    """Create a new execution run from a failed one with a fresh idempotency key."""
    orig_result = await db.execute(
        select(ExecutionRun).where(
            ExecutionRun.id == run_id, ExecutionRun.tenant_id == user.tenant_id
        )
    )
    orig = orig_result.scalar_one_or_none()
    if not orig:
        raise HTTPException(status_code=404, detail="Execution run not found")
    if orig.status not in ("failed",):
        raise HTTPException(status_code=400, detail="Only failed runs can be retried")

    new_key = hashlib.sha256(f"{orig.idempotency_key}:retry:{time.time()}".encode()).hexdigest()

    retry_run = ExecutionRun(
        tenant_id=orig.tenant_id,
        created_by=user.user_id,
        campaign_id=orig.campaign_id,
        asset_id=orig.asset_id,
        approval_id=orig.approval_id,
        channel=orig.channel,
        provider=orig.provider,
        idempotency_key=new_key,
        status="queued",
        executed_by=user.user_id,
    )
    db.add(retry_run)
    await db.flush()
    await log_action(
        db, tenant_id=user.tenant_id, actor_id=user.user_id,
        actor_email=user.email, action="execution.retry_queued",
        resource_type="execution_run", resource_id=str(retry_run.id),
    )
    return retry_run


@router.post("/run", response_model=ExecutionRunRead, status_code=status.HTTP_201_CREATED)
async def run_execution(payload: ExecutionRequest, db: DB, user: CurrentUser):
    if "workspace_admin" not in user.roles and "marketing_lead" not in user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to execute")

    # ── Verify approval ───────────────────────────────────────────────────────
    ap_result = await db.execute(
        select(Approval).where(
            Approval.id == payload.approval_id,
            Approval.tenant_id == user.tenant_id,
            Approval.status == "approved",
        )
    )
    if not ap_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Approval not found or not approved")

    # ── Spend gate ────────────────────────────────────────────────────────────
    camp_result = await db.execute(
        select(Campaign).where(Campaign.id == payload.campaign_id, Campaign.tenant_id == user.tenant_id)
    )
    campaign = camp_result.scalar_one_or_none()
    if campaign and campaign.budget:
        spend_result = await db.execute(
            select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
                AnalyticsEvent.campaign_id == payload.campaign_id,
                AnalyticsEvent.event_type == "spend",
                AnalyticsEvent.tenant_id == user.tenant_id,
            )
        )
        total_spend = float(spend_result.scalar_one() or 0)
        if total_spend >= float(campaign.budget):
            raise HTTPException(
                status_code=402,
                detail=f"Campaign budget of ${campaign.budget:.2f} exhausted (spent: ${total_spend:.2f}). Update the budget to continue.",
            )

    # ── Idempotency check ─────────────────────────────────────────────────────
    idempotency_key = make_idempotency_key(payload.campaign_id, payload.asset_id, payload.channel)
    existing = await db.execute(
        select(ExecutionRun).where(ExecutionRun.idempotency_key == idempotency_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Execution already ran for this asset/channel")

    # ── Asset + variant ───────────────────────────────────────────────────────
    asset_result = await db.execute(
        select(ContentAsset).where(
            ContentAsset.id == payload.asset_id, ContentAsset.tenant_id == user.tenant_id
        )
    )
    if not asset_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Asset not found")

    variant_result = await db.execute(
        select(ContentVariant).where(
            ContentVariant.asset_id == payload.asset_id,
            ContentVariant.is_active == True,
        )
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=400, detail="No active variant found")

    # ── Channel config (HubSpot list, ad set IDs, etc.) ──────────────────────
    channel_result = await db.execute(
        select(CampaignChannel).where(
            CampaignChannel.campaign_id == payload.campaign_id,
            CampaignChannel.channel == payload.channel,
            CampaignChannel.tenant_id == user.tenant_id,
        )
    )
    campaign_channel = channel_result.scalar_one_or_none()
    channel_config = campaign_channel.config if campaign_channel else {}

    # ── Create execution run ──────────────────────────────────────────────────
    run = ExecutionRun(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_id,
        approval_id=payload.approval_id,
        channel=payload.channel,
        provider=payload.provider,
        idempotency_key=idempotency_key,
        status="running",
        executed_by=user.user_id,
    )
    db.add(run)
    await db.flush()

    # ── Resolve recipients for email channels ─────────────────────────────────
    to_emails: list[str] = []
    if payload.channel == "email":
        to_emails = await resolve_email_recipients(
            hubspot_list_id=channel_config.get("hubspot_list_id"),
        )

    # ── Dispatch via MCP Gateway ──────────────────────────────────────────────
    result = await gateway.dispatch(
        db,
        tenant_id=user.tenant_id,
        provider=payload.provider,
        channel=payload.channel,
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_id,
        execution_run_id=run.id,
        variant_body=dict(variant.body),
        to_emails=to_emails,
        extra=channel_config,
    )

    run.status = "success" if result.success else "failed"
    run.provider_id = result.provider_job_id
    run.result = result.raw_response
    if not result.success:
        run.error_message = result.error

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action=f"execution.{run.status}",
        resource_type="execution_run",
        resource_id=str(run.id),
        summary=f"Channel: {payload.channel}, Provider: {payload.provider}, Status: {run.status}",
        metadata={"idempotency_key": idempotency_key, "gateway_job": result.provider_job_id},
    )
    return run
