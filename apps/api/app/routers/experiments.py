"""
Experiment router — create and manage A/B tests for content assets.

Flow:
  1. POST /api/experiments                  — create experiment for an asset
  2. POST /api/experiments/{id}/record-event — track impressions/clicks/conversions
  3. GET  /api/experiments/{id}              — live stats + significance per variant
  4. POST /api/experiments/{id}/conclude     — declare winner + optionally promote
  5. POST /api/experiments/{id}/set-weights  — adjust variant traffic split
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from app.models.content import ContentAsset, ContentVariant
from app.models.experiment import Experiment
from app.routers.deps import DB, CurrentUser
from app.schemas.experiment import (
    ConcludeRequest,
    ExperimentCreate,
    ExperimentDetailRead,
    ExperimentRead,
    ExperimentUpdate,
    RecordEventRequest,
    SetWeightsRequest,
    VariantStats,
)
from app.services.audit import log_action
from app.services.experiment import (
    compute_variant_stats_raw,
    enrich_stats_with_significance,
    select_variant,
)

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_experiment_or_404(db: DB, experiment_id: uuid.UUID, tenant_id: uuid.UUID) -> Experiment:
    result = await db.execute(
        select(Experiment).where(
            Experiment.id == experiment_id,
            Experiment.tenant_id == tenant_id,
        )
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


async def _build_detail(
    db: DB,
    exp: Experiment,
    variants: list[ContentVariant],
) -> ExperimentDetailRead:
    """Attach live stats to an experiment."""
    variant_ids = [v.id for v in variants]
    raw = await compute_variant_stats_raw(
        db, asset_id=exp.asset_id, tenant_id=exp.tenant_id, variant_ids=variant_ids
    )

    # Control = variant with lowest version number
    control = min(variants, key=lambda v: v.version) if variants else None
    control_id = str(control.id) if control else (str(variant_ids[0]) if variant_ids else "")
    enriched = enrich_stats_with_significance(raw, control_id)

    stats_list: list[VariantStats] = []
    for v in variants:
        vid = str(v.id)
        s = enriched.get(vid, {"impressions": 0, "clicks": 0, "conversions": 0, "ctr": 0.0, "cvr": 0.0, "confidence": 0.0, "is_control": False})
        stats_list.append(
            VariantStats(
                variant_id=v.id,
                version=v.version,
                traffic_weight=float(v.traffic_weight or 1.0),
                impressions=s["impressions"],
                clicks=s["clicks"],
                conversions=s["conversions"],
                ctr=s["ctr"],
                cvr=s["cvr"],
                confidence=s["confidence"],
                is_control=s["is_control"],
                is_winner=(v.id == exp.winner_variant_id),
            )
        )

    total_impressions = sum(s.impressions for s in stats_list)
    # Best treatment = highest confidence above control
    treatments = [s for s in stats_list if not s.is_control]
    leading = max(treatments, key=lambda s: s.confidence) if treatments else None

    return ExperimentDetailRead(
        **ExperimentRead.model_validate(exp).model_dump(),
        variant_stats=stats_list,
        total_impressions=total_impressions,
        leading_variant_id=leading.variant_id if leading else None,
        leading_confidence=leading.confidence if leading else 0.0,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ExperimentDetailRead, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: ExperimentCreate, db: DB, user: CurrentUser):
    # Verify asset belongs to tenant
    asset_result = await db.execute(
        select(ContentAsset).where(
            ContentAsset.id == payload.asset_id,
            ContentAsset.tenant_id == user.tenant_id,
        )
    )
    if not asset_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Asset not found")

    # Only one running experiment per asset
    existing = await db.execute(
        select(Experiment).where(
            Experiment.asset_id == payload.asset_id,
            Experiment.tenant_id == user.tenant_id,
            Experiment.status == "running",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A running experiment already exists for this asset")

    exp = Experiment(
        tenant_id=user.tenant_id,
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_id,
        name=payload.name,
        hypothesis=payload.hypothesis,
        confidence_threshold=payload.confidence_threshold,
        auto_promote=payload.auto_promote,
        status="running",
        created_by=user.user_id,
    )
    db.add(exp)
    await db.flush()

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == payload.asset_id)
        .order_by(ContentVariant.version)
    )
    variants = list(variants_result.scalars().all())

    await log_action(
        db, tenant_id=user.tenant_id, actor_id=user.user_id, actor_email=user.email,
        action="experiment.created", resource_type="experiment", resource_id=str(exp.id),
        summary=f"Experiment '{exp.name}' created for asset {exp.asset_id}",
    )
    return await _build_detail(db, exp, variants)


@router.get("/campaign/{campaign_id}", response_model=list[ExperimentRead])
async def list_campaign_experiments(campaign_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(Experiment).where(
            Experiment.campaign_id == campaign_id,
            Experiment.tenant_id == user.tenant_id,
        ).order_by(Experiment.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{experiment_id}", response_model=ExperimentDetailRead)
async def get_experiment(experiment_id: uuid.UUID, db: DB, user: CurrentUser):
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)
    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == exp.asset_id)
        .order_by(ContentVariant.version)
    )
    variants = list(variants_result.scalars().all())
    return await _build_detail(db, exp, variants)


@router.patch("/{experiment_id}", response_model=ExperimentRead)
async def update_experiment(experiment_id: uuid.UUID, payload: ExperimentUpdate, db: DB, user: CurrentUser):
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)
    if exp.status == "concluded":
        raise HTTPException(status_code=400, detail="Cannot update a concluded experiment")

    if payload.name is not None:
        exp.name = payload.name
    if payload.hypothesis is not None:
        exp.hypothesis = payload.hypothesis
    if payload.status is not None:
        if payload.status not in ("running", "paused"):
            raise HTTPException(status_code=400, detail="status must be 'running' or 'paused'")
        exp.status = payload.status
    if payload.confidence_threshold is not None:
        exp.confidence_threshold = payload.confidence_threshold
    if payload.auto_promote is not None:
        exp.auto_promote = payload.auto_promote

    return exp


@router.post("/{experiment_id}/set-weights", response_model=ExperimentDetailRead)
async def set_variant_weights(experiment_id: uuid.UUID, payload: SetWeightsRequest, db: DB, user: CurrentUser):
    """Adjust the traffic split — e.g. 50/50, 80/20, etc."""
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == exp.asset_id)
    )
    variants = list(variants_result.scalars().all())

    for v in variants:
        new_weight = payload.weights.get(str(v.id))
        if new_weight is not None:
            if new_weight < 0:
                raise HTTPException(status_code=400, detail=f"Weight for {v.id} must be >= 0")
            v.traffic_weight = new_weight

    return await _build_detail(db, exp, variants)


@router.post("/{experiment_id}/select-variant")
async def select_experiment_variant(experiment_id: uuid.UUID, db: DB, user: CurrentUser):
    """
    Weighted random variant selection — call this before serving/sending content
    to determine which variant the current user/send should receive.
    Does NOT record an impression automatically; call record-event separately.
    """
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)
    if exp.status != "running":
        raise HTTPException(status_code=400, detail="Experiment is not running")

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == exp.asset_id)
        .order_by(ContentVariant.version)
    )
    variants = list(variants_result.scalars().all())
    if not variants:
        raise HTTPException(status_code=404, detail="No variants found for this asset")

    chosen = select_variant(variants)
    return {
        "variant_id": str(chosen.id),
        "version": chosen.version,
        "traffic_weight": chosen.traffic_weight,
        "body": chosen.body,
    }


@router.post("/{experiment_id}/record-event", status_code=status.HTTP_201_CREATED)
async def record_experiment_event(
    experiment_id: uuid.UUID, payload: RecordEventRequest, db: DB, user: CurrentUser
):
    """
    Record an impression, click, or conversion for a specific variant.
    This writes to analytics_events with the variant_id set, enabling
    per-variant stats and significance computation.
    """
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)

    if payload.event_type not in ("impression", "click", "conversion"):
        raise HTTPException(status_code=400, detail="event_type must be impression, click, or conversion")

    # Verify variant belongs to this experiment's asset
    variant_result = await db.execute(
        select(ContentVariant).where(
            ContentVariant.id == payload.variant_id,
            ContentVariant.asset_id == exp.asset_id,
        )
    )
    if not variant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Variant not found in this experiment")

    event = AnalyticsEvent(
        tenant_id=user.tenant_id,
        campaign_id=exp.campaign_id,
        asset_id=exp.asset_id,
        variant_id=payload.variant_id,
        event_type=payload.event_type,
        value=payload.value,
        properties={"experiment_id": str(experiment_id)},
    )
    db.add(event)
    await db.flush()

    # Auto-check for winner if this is a conversion event
    if payload.event_type == "conversion" and exp.status == "running" and exp.auto_promote:
        await _check_for_winner(db, exp)

    return {"status": "ok", "event_id": str(event.id)}


@router.post("/{experiment_id}/conclude", response_model=ExperimentDetailRead)
async def conclude_experiment(
    experiment_id: uuid.UUID, payload: ConcludeRequest, db: DB, user: CurrentUser
):
    """
    Conclude an experiment. Optionally specify a winner_variant_id.
    If promote=True and a winner is set, promotes winner to is_active=True.
    """
    exp = await _get_experiment_or_404(db, experiment_id, user.tenant_id)
    if exp.status == "concluded":
        raise HTTPException(status_code=400, detail="Experiment already concluded")

    exp.status = "concluded"
    exp.concluded_at = datetime.now(timezone.utc)

    if payload.winner_variant_id:
        exp.winner_variant_id = payload.winner_variant_id
        if payload.promote:
            await _promote_winner(db, exp.asset_id, payload.winner_variant_id, user.tenant_id)

    await log_action(
        db, tenant_id=user.tenant_id, actor_id=user.user_id, actor_email=user.email,
        action="experiment.concluded", resource_type="experiment", resource_id=str(exp.id),
        summary=f"Experiment '{exp.name}' concluded. Winner: {payload.winner_variant_id or 'inconclusive'}",
    )

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == exp.asset_id)
        .order_by(ContentVariant.version)
    )
    return await _build_detail(db, exp, list(variants_result.scalars().all()))


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _promote_winner(
    db: DB, asset_id: uuid.UUID, winner_id: uuid.UUID, tenant_id: uuid.UUID
) -> None:
    """Set winner variant as active, deactivate all others."""
    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == asset_id)
    )
    for v in variants_result.scalars().all():
        v.is_active = (v.id == winner_id)


async def _check_for_winner(db: DB, exp: Experiment) -> None:
    """
    After each conversion event, check if any treatment variant has reached
    the confidence threshold. If so, auto-conclude and promote.
    """
    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.asset_id == exp.asset_id)
        .order_by(ContentVariant.version)
    )
    variants = list(variants_result.scalars().all())
    if len(variants) < 2:
        return

    raw = await compute_variant_stats_raw(
        db, asset_id=exp.asset_id, tenant_id=exp.tenant_id, variant_ids=[v.id for v in variants]
    )

    control = min(variants, key=lambda v: v.version)
    ctrl = raw.get(str(control.id), {"impressions": 0, "conversions": 0})

    for v in variants:
        if v.id == control.id:
            continue
        s = raw.get(str(v.id), {"impressions": 0, "conversions": 0})
        # Require minimum sample size before concluding
        if s["impressions"] < 30 or ctrl["impressions"] < 30:
            continue
        from app.services.experiment import two_prop_z_test
        confidence = two_prop_z_test(
            ctrl["impressions"], ctrl["conversions"],
            s["impressions"], s["conversions"],
        )
        if confidence >= exp.confidence_threshold:
            # Treatment is winning — conclude and promote
            exp.status = "concluded"
            exp.concluded_at = datetime.now(timezone.utc)
            exp.winner_variant_id = v.id
            await _promote_winner(db, exp.asset_id, v.id, exp.tenant_id)
            break
