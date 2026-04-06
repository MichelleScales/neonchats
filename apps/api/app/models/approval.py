import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedBase


class Approval(TenantScopedBase):
    __tablename__ = "approvals"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_variants.id", ondelete="SET NULL"), nullable=True
    )
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # content | publish | spend | outbound

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    # pending | approved | rejected | changes_requested

    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    due_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    policy_check_results: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # { brand: pass|fail, claims: pass|fail, pii: pass|fail, links: pass|fail }

    release_target: Mapped[str | None] = mapped_column(String(255), nullable=True)

    comments: Mapped[list["ApprovalComment"]] = relationship(
        "ApprovalComment", back_populates="approval", cascade="all, delete-orphan"
    )


class ApprovalComment(TenantScopedBase):
    __tablename__ = "approval_comments"

    approval_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    approval: Mapped["Approval"] = relationship("Approval", back_populates="comments")
