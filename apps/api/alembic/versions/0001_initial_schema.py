"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── tenants ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )

    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("permissions", JSONB, nullable=False, server_default="[]"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── voice packs ───────────────────────────────────────────────────────────
    op.create_table(
        "voice_packs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("tone", JSONB, nullable=False, server_default="{}"),
        sa.Column("vocabulary", JSONB, nullable=False, server_default="[]"),
        sa.Column("banned_phrases", JSONB, nullable=False, server_default="[]"),
        sa.Column("claims_policy", JSONB, nullable=False, server_default="{}"),
        sa.Column("style_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "canon_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("voice_pack_id", UUID(as_uuid=True), sa.ForeignKey("voice_packs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),  # overridden by pgvector below
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Replace Text column with vector(1536)
    op.execute("ALTER TABLE canon_documents DROP COLUMN embedding")
    op.execute("ALTER TABLE canon_documents ADD COLUMN embedding vector(1536)")

    # ── campaigns ─────────────────────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft", index=True),
        sa.Column("goal", sa.Text, nullable=True),
        sa.Column("audience_summary", sa.Text, nullable=True),
        sa.Column("offer", JSONB, nullable=False, server_default="{}"),
        sa.Column("brief", sa.Text, nullable=True),
        sa.Column("compliance_notes", sa.Text, nullable=True),
        sa.Column("launch_at", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "campaign_channels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── content ───────────────────────────────────────────────────────────────
    op.create_table(
        "content_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("voice_pack_id", UUID(as_uuid=True), sa.ForeignKey("voice_packs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "content_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("body", JSONB, nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("approval_state", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("source_documents", JSONB, nullable=False, server_default="[]"),
        sa.Column("banned_phrase_flags", JSONB, nullable=False, server_default="[]"),
        sa.Column("claim_warnings", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── approvals ─────────────────────────────────────────────────────────────
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("content_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending", index=True),
        sa.Column("requester_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.String(50), nullable=True),
        sa.Column("policy_check_results", JSONB, nullable=False, server_default="{}"),
        sa.Column("release_target", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "approval_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── executions ────────────────────────────────────────────────────────────
    op.create_table(
        "execution_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued", index=True),
        sa.Column("params_hash", sa.String(64), nullable=True),
        sa.Column("response_hash", sa.String(64), nullable=True),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column("result", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("executed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── analytics events ──────────────────────────────────────────────────────
    op.create_table(
        "analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("execution_run_id", UUID(as_uuid=True), sa.ForeignKey("execution_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("properties", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # ── audit log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("analytics_events")
    op.drop_table("execution_runs")
    op.drop_table("approval_comments")
    op.drop_table("approvals")
    op.drop_table("content_variants")
    op.drop_table("content_assets")
    op.drop_table("campaign_channels")
    op.drop_table("campaigns")
    op.drop_table("canon_documents")
    op.drop_table("voice_packs")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute("DROP EXTENSION IF EXISTS vector")
