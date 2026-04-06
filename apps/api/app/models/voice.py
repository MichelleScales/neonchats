import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedBase


class VoicePack(TenantScopedBase):
    __tablename__ = "voice_packs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Tone sliders: formal↔casual, serious↔playful, etc.
    tone: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    vocabulary: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # preferred words, power words, brand-specific terms

    banned_phrases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    claims_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # { allowed_claims: [], forbidden_claims: [], requires_approval: [] }

    style_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Compressed distillation used as system prompt prefix

    canon_documents: Mapped[list["CanonDocument"]] = relationship(
        "CanonDocument", back_populates="voice_pack", cascade="all, delete-orphan"
    )


class CanonDocument(TenantScopedBase):
    __tablename__ = "canon_documents"

    voice_pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("voice_packs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # upload | website | manual

    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # email | social | landing_page | ad — for retrieval filtering

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    # 1536 dims for OpenAI/Anthropic compatible embeddings

    voice_pack: Mapped["VoicePack"] = relationship("VoicePack", back_populates="canon_documents")
