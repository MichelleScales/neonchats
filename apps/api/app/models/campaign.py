from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedBase


class Campaign(TenantScopedBase):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    # draft | pending_approval | approved | executing | live | paused | complete | archived

    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # { headline, body, cta, discount_code, ... }

    brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    launch_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Relations
    channels: Mapped[list["CampaignChannel"]] = relationship(
        "CampaignChannel", back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignChannel(TenantScopedBase):
    __tablename__ = "campaign_channels"

    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # email | social | landing_page | ad | sms

    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # channel-specific settings: list_id, from_name, ad_account, etc.

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="channels")
