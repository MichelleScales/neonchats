import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.content import ContentAsset, ContentVariant
from app.models.voice import VoicePack, CanonDocument
from app.routers.deps import DB, CurrentUser
from app.schemas.content import ContentAssetRead, GenerateAssetRequest, RewriteRequest
from app.services.audit import log_action
from app.services.content_generator import generate_variants
from app.services.rag import retrieve_canon_examples

router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/generate", response_model=ContentAssetRead, status_code=status.HTTP_201_CREATED)
async def generate_asset(payload: GenerateAssetRequest, db: DB, user: CurrentUser):
    # Fetch campaign for context
    camp_result = await db.execute(
        select(Campaign).where(
            Campaign.id == payload.campaign_id, Campaign.tenant_id == user.tenant_id
        )
    )
    campaign = camp_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Fetch voice pack if specified
    voice_pack_data = None
    banned_phrases: list[str] = []
    claims_policy: dict = {}
    canon_examples: list[str] = []

    if payload.voice_pack_id:
        vp_result = await db.execute(
            select(VoicePack).where(
                VoicePack.id == payload.voice_pack_id,
                VoicePack.tenant_id == user.tenant_id,
            )
        )
        vp = vp_result.scalar_one_or_none()
        if vp:
            voice_pack_data = {
                "style_summary": vp.style_summary,
                "vocabulary": vp.vocabulary,
                "banned_phrases": vp.banned_phrases,
            }
            banned_phrases = vp.banned_phrases
            claims_policy = vp.claims_policy
            # Build a retrieval query from the campaign context
            rag_query = f"{payload.asset_type} {campaign.goal or ''} {campaign.audience_summary or ''}"
            retrieved = await retrieve_canon_examples(
                db,
                tenant_id=user.tenant_id,
                voice_pack_id=payload.voice_pack_id,
                query=rag_query,
                channel=payload.channel,
                top_k=5,
            )
            canon_examples = [r["content"] for r in retrieved if r.get("content")]

    # Generate variants via AI
    raw_variants = await generate_variants(
        asset_type=payload.asset_type,
        campaign_context={
            "name": campaign.name,
            "goal": campaign.goal,
            "audience_summary": campaign.audience_summary,
            "offer": campaign.offer,
        },
        brief=payload.brief or campaign.brief,
        variant_count=payload.variant_count,
        voice_pack_data=voice_pack_data,
        canon_examples=canon_examples,
        banned_phrases=banned_phrases,
        claims_policy=claims_policy,
    )

    # Persist asset + variants
    asset = ContentAsset(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        campaign_id=campaign.id,
        asset_type=payload.asset_type,
        channel=payload.channel,
        voice_pack_id=payload.voice_pack_id,
    )
    db.add(asset)
    await db.flush()

    for i, rv in enumerate(raw_variants, 1):
        db.add(ContentVariant(
            tenant_id=user.tenant_id,
            created_by=user.user_id,
            asset_id=asset.id,
            version=i,
            body=rv["body"],
            model_used=rv["model_used"],
            prompt_hash=rv["prompt_hash"],
            quality_score=rv["quality_score"],
            banned_phrase_flags=rv["banned_phrase_flags"],
            claim_warnings=rv["claim_warnings"],
        ))

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="content.generated",
        resource_type="content_asset",
        resource_id=str(asset.id),
        summary=f"Generated {payload.variant_count} {payload.asset_type} variants for campaign {campaign.name}",
    )

    await db.refresh(asset, ["variants"])
    return asset


@router.get("/campaign/{campaign_id}", response_model=list[ContentAssetRead])
async def list_campaign_assets(campaign_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ContentAsset)
        .where(ContentAsset.campaign_id == campaign_id, ContentAsset.tenant_id == user.tenant_id)
        .options(selectinload(ContentAsset.variants))
        .order_by(ContentAsset.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{asset_id}", response_model=ContentAssetRead)
async def get_asset(asset_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ContentAsset)
        .where(ContentAsset.id == asset_id, ContentAsset.tenant_id == user.tenant_id)
        .options(selectinload(ContentAsset.variants))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/{asset_id}/rewrite", response_model=ContentAssetRead)
async def rewrite_asset(asset_id: uuid.UUID, payload: RewriteRequest, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ContentAsset)
        .where(ContentAsset.id == asset_id, ContentAsset.tenant_id == user.tenant_id)
        .options(selectinload(ContentAsset.variants))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Deactivate old active variants
    active = [v for v in asset.variants if v.is_active]
    next_version = max((v.version for v in asset.variants), default=0) + 1

    # Regenerate with instruction appended to brief
    camp_result = await db.execute(select(Campaign).where(Campaign.id == asset.campaign_id))
    campaign = camp_result.scalar_one()

    raw_variants = await generate_variants(
        asset_type=asset.asset_type,
        campaign_context={
            "name": campaign.name,
            "goal": campaign.goal,
            "audience_summary": campaign.audience_summary,
            "offer": campaign.offer,
        },
        brief=payload.instruction,
        variant_count=1,
        voice_pack_data=None,
        canon_examples=[],
        banned_phrases=[],
        claims_policy={},
    )

    for v in active:
        v.is_active = False

    rv = raw_variants[0]
    new_variant = ContentVariant(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        asset_id=asset.id,
        version=next_version,
        body=rv["body"],
        model_used=rv["model_used"],
        prompt_hash=rv["prompt_hash"],
        quality_score=rv["quality_score"],
        banned_phrase_flags=rv["banned_phrase_flags"],
        claim_warnings=rv["claim_warnings"],
    )
    db.add(new_variant)

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="content.rewritten",
        resource_type="content_asset",
        resource_id=str(asset.id),
        summary=f"Rewrite: {payload.instruction}",
    )

    await db.refresh(asset, ["variants"])
    return asset


@router.post("/{asset_id}/submit", response_model=ContentAssetRead)
async def submit_for_approval(asset_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ContentAsset)
        .where(ContentAsset.id == asset_id, ContentAsset.tenant_id == user.tenant_id)
        .options(selectinload(ContentAsset.variants))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.status = "review"
    for v in asset.variants:
        if v.is_active:
            v.approval_state = "submitted"

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="content.submitted",
        resource_type="content_asset",
        resource_id=str(asset.id),
    )
    return asset
