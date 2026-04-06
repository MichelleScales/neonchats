import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedBase


class ContentAsset(TenantScopedBase):
    __tablename__ = "content_assets"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # email | social_post | landing_page | ad_copy | seo_article

    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    # draft | review | approved | published | archived

    voice_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voice_packs.id", ondelete="SET NULL"), nullable=True
    )

    variants: Mapped[list["ContentVariant"]] = relationship(
        "ContentVariant", back_populates="asset", cascade="all, delete-orphan"
    )


class ContentVariant(TenantScopedBase):
    __tablename__ = "content_variants"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # The body is a flexible JSON blob to support all channel types.
    # email: { subject, preheader, html_body, text_body }
    # social: { caption, hashtags, image_prompt }
    # landing_page: { headline, subheadline, sections: [...], cta }
    # ad_copy: { headline, description, cta }
    body: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # A/B experiment traffic allocation weight (relative, not a percentage)
    traffic_weight: Mapped[float] = mapped_column(nullable=False, default=1.0)

    quality_score: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    approval_state: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # pending | submitted | approved | rejected

    # Generation provenance
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_documents: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # list of canon_document IDs + voice_pack version used
    banned_phrase_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    claim_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    asset: Mapped["ContentAsset"] = relationship("ContentAsset", back_populates="variants")
