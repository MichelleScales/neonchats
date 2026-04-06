import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, CampaignChannel
from app.routers.deps import DB, CurrentUser
from app.schemas.campaign import CampaignCreate, CampaignList, CampaignRead, CampaignUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, db: DB, user: CurrentUser):
    campaign = Campaign(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        name=payload.name,
        goal=payload.goal,
        audience_summary=payload.audience_summary,
        offer=payload.offer,
        brief=payload.brief,
        compliance_notes=payload.compliance_notes,
        launch_at=payload.launch_at,
    )
    db.add(campaign)
    await db.flush()

    for ch in payload.channels:
        db.add(CampaignChannel(
            tenant_id=user.tenant_id,
            created_by=user.user_id,
            campaign_id=campaign.id,
            channel=ch,
        ))

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="campaign.created",
        resource_type="campaign",
        resource_id=str(campaign.id),
        summary=f"Campaign '{campaign.name}' created",
    )
    await db.refresh(campaign, ["channels"])
    return campaign


@router.get("", response_model=CampaignList)
async def list_campaigns(
    db: DB,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    q = select(Campaign).where(Campaign.tenant_id == user.tenant_id)
    if status:
        q = q.where(Campaign.status == status)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.options(selectinload(Campaign.channels)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return CampaignList(items=list(items), total=total, page=page, page_size=page_size)


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(campaign_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.tenant_id == user.tenant_id)
        .options(selectinload(Campaign.channels))
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(campaign_id: uuid.UUID, payload: CampaignUpdate, db: DB, user: CurrentUser):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.tenant_id == user.tenant_id)
        .options(selectinload(Campaign.channels))
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="campaign.updated",
        resource_type="campaign",
        resource_id=str(campaign.id),
        summary=f"Campaign '{campaign.name}' updated",
        metadata=payload.model_dump(exclude_none=True),
    )
    return campaign
