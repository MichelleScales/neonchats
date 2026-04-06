import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.voice import VoicePack, CanonDocument
from app.routers.deps import DB, CurrentUser
from app.schemas.voice import (
    CanonDocumentRead, IngestRequest,
    VoicePackCreate, VoicePackRead, VoicePackUpdate,
)
from app.services.audit import log_action
from app.services.rag import embed_and_store_document

router = APIRouter(prefix="/api/voice-packs", tags=["voice"])


@router.get("", response_model=list[VoicePackRead])
async def list_voice_packs(db: DB, user: CurrentUser):
    result = await db.execute(
        select(VoicePack).where(VoicePack.tenant_id == user.tenant_id)
    )
    return result.scalars().all()


@router.post("", response_model=VoicePackRead, status_code=status.HTTP_201_CREATED)
async def create_voice_pack(payload: VoicePackCreate, db: DB, user: CurrentUser):
    vp = VoicePack(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        name=payload.name,
        tone=payload.tone,
        vocabulary=payload.vocabulary,
        banned_phrases=payload.banned_phrases,
        claims_policy=payload.claims_policy,
        style_summary=payload.style_summary,
    )
    db.add(vp)
    await db.flush()
    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="voice_pack.created",
        resource_type="voice_pack",
        resource_id=str(vp.id),
        summary=f"Voice pack '{vp.name}' created",
    )
    return vp


@router.patch("/{voice_pack_id}", response_model=VoicePackRead)
async def update_voice_pack(voice_pack_id: uuid.UUID, payload: VoicePackUpdate, db: DB, user: CurrentUser):
    result = await db.execute(
        select(VoicePack).where(VoicePack.id == voice_pack_id, VoicePack.tenant_id == user.tenant_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail="Voice pack not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(vp, field, value)

    # Bump version on substantive changes
    if any(f in payload.model_dump(exclude_none=True) for f in ["tone", "vocabulary", "banned_phrases", "claims_policy"]):
        vp.version += 1

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="voice_pack.updated",
        resource_type="voice_pack",
        resource_id=str(vp.id),
    )
    return vp


@router.post("/{voice_pack_id}/ingest", response_model=CanonDocumentRead)
async def ingest_document(voice_pack_id: uuid.UUID, payload: IngestRequest, db: DB, user: CurrentUser):
    result = await db.execute(
        select(VoicePack).where(VoicePack.id == voice_pack_id, VoicePack.tenant_id == user.tenant_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail="Voice pack not found")

    content = payload.content
    if payload.source_type == "website" and payload.source_url and not content:
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(payload.source_url, timeout=15)
                content = resp.text[:10000]  # First 10k chars
            except Exception:
                content = ""

    doc = CanonDocument(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        voice_pack_id=voice_pack_id,
        title=payload.source_url or "Uploaded document",
        source_type=payload.source_type,
        source_url=payload.source_url,
        content=content,
        channel=payload.channel,
    )
    db.add(doc)
    await db.flush()

    # Auto-generate embedding for semantic retrieval
    try:
        await embed_and_store_document(db, doc)
    except Exception:
        pass  # Non-fatal — document is stored, just without embedding

    await log_action(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.user_id,
        actor_email=user.email,
        action="voice_pack.document_ingested",
        resource_type="canon_document",
        resource_id=str(doc.id),
    )
    return doc
