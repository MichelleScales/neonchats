import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.models.analytics import AnalyticsEvent
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.content import ContentAsset, ContentVariant
from app.models.execution import ExecutionRun
from app.routers.deps import DB, CurrentUser
from app.schemas.execution import ExecutionRequest, ExecutionRunRead
from app.services.audit import log_action
from app.models.campaign import CampaignChannel
from app.services.execution import make_idempotency_key, send_email_sendgrid, publish_social_post, resolve_email_recipients

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
    """Create a new execution run from a failed one, with a fresh idempotency key."""
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

    import hashlib, time
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
    await log_action(db, tenant_id=user.tenant_id, actor_id=user.user_id,
                     actor_email=user.email, action="execution.retry_queued",
                     resource_type="execution_run", resource_id=str(retry_run.id))
    return retry_run


@router.post("/run", response_model=ExecutionRunRead, status_code=status.HTTP_201_CREATED)
async def run_execution(payload: ExecutionRequest, db: DB, user: CurrentUser):
    if "workspace_admin" not in user.roles and "marketing_lead" not in user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to execute")

    # Verify approval
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
                detail=f"Campaign budget of ${campaign.budget:.2f} exhausted (spent: ${total_spend:.2f}). Update the budget to continue."
            )

    idempotency_key = make_idempotency_key(payload.campaign_id, payload.asset_id, payload.channel)

    # Check for duplicate
    existing = await db.execute(
        select(ExecutionRun).where(ExecutionRun.idempotency_key == idempotency_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Execution already ran for this asset/channel")

    # Get active variant body
    asset_result = await db.execute(
        select(ContentAsset).where(
            ContentAsset.id == payload.asset_id, ContentAsset.tenant_id == user.tenant_id
        )
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
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

    # Resolve HubSpot list ID from CampaignChannel config (Phase 2)
    channel_result = await db.execute(
        select(CampaignChannel).where(
            CampaignChannel.campaign_id == payload.campaign_id,
            CampaignChannel.channel == payload.channel,
            CampaignChannel.tenant_id == user.tenant_id,
        )
    )
    campaign_channel = channel_result.scalar_one_or_none()
    hubspot_list_id = (campaign_channel.config or {}).get("hubspot_list_id") if campaign_channel else None

    # Execute via provider
    try:
        if payload.channel == "email" and payload.provider == "sendgrid":
            to_emails = await resolve_email_recipients(hubspot_list_id=hubspot_list_id)
            result = await send_email_sendgrid(
                to_emails=to_emails,
                subject=variant.body.get("subject", ""),
                html_body=variant.body.get("html_body", ""),
                text_body=variant.body.get("text_body", ""),
            )
        else:
            result = await publish_social_post(
                provider=payload.provider,
                caption=variant.body.get("caption", ""),
                hashtags=variant.body.get("hashtags", []),
                config={},
            )
        run.status = "success"
        run.result = result
        run.provider_id = result.get("message_id") or result.get("provider_id")
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action=f"execution.{run.status}",
        resource_type="execution_run",
        resource_id=str(run.id),
        summary=f"Channel: {payload.channel}, Provider: {payload.provider}, Status: {run.status}",
        metadata={"idempotency_key": idempotency_key},
    )
    return run
