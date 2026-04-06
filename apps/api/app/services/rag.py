"""
RAG retrieval service — finds the most relevant canon documents for a given
generation request using cosine similarity via pgvector.
"""

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice import CanonDocument
from app.services.embeddings import embed_text


async def retrieve_canon_examples(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    voice_pack_id: uuid.UUID,
    query: str,
    channel: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-k most relevant canon documents for a query.
    Uses pgvector cosine similarity (<=> operator).
    Falls back to recency-ordered results if no embeddings exist.
    """
    query_embedding = await embed_text(query)

    # Check if any documents have embeddings
    count_result = await db.execute(
        select(CanonDocument).where(
            CanonDocument.voice_pack_id == voice_pack_id,
            CanonDocument.tenant_id == tenant_id,
            CanonDocument.embedding.isnot(None),
        ).limit(1)
    )
    has_embeddings = count_result.scalar_one_or_none() is not None

    if has_embeddings:
        # Vector similarity search
        channel_filter = "AND channel = :channel" if channel else ""
        sql = text(f"""
            SELECT id, title, content, channel,
                   embedding <=> CAST(:embedding AS vector) AS distance
            FROM canon_documents
            WHERE voice_pack_id = :voice_pack_id
              AND tenant_id = :tenant_id
              AND embedding IS NOT NULL
              AND content IS NOT NULL
              {channel_filter}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        params: dict[str, Any] = {
            "embedding": str(query_embedding),
            "voice_pack_id": str(voice_pack_id),
            "tenant_id": str(tenant_id),
            "top_k": top_k,
        }
        if channel:
            params["channel"] = channel

        result = await db.execute(sql, params)
        rows = result.fetchall()
        return [
            {"id": str(r.id), "title": r.title, "content": r.content, "distance": r.distance}
            for r in rows
        ]
    else:
        # Fallback: return most recent documents
        q = select(CanonDocument).where(
            CanonDocument.voice_pack_id == voice_pack_id,
            CanonDocument.tenant_id == tenant_id,
            CanonDocument.content.isnot(None),
        )
        if channel:
            q = q.where(CanonDocument.channel == channel)
        q = q.order_by(CanonDocument.created_at.desc()).limit(top_k)
        result = await db.execute(q)
        docs = result.scalars().all()
        return [
            {"id": str(d.id), "title": d.title, "content": d.content, "distance": None}
            for d in docs
        ]


async def embed_and_store_document(
    db: AsyncSession,
    doc: CanonDocument,
) -> None:
    """Generate and store an embedding for a single canon document."""
    if not doc.content:
        return
    from app.services.embeddings import embed_text as _embed
    embedding = await _embed(doc.content)
    doc.embedding = embedding
    await db.flush()
