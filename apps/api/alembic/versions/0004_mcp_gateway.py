"""Add MCP Gateway — connector_credentials and connector_jobs tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── connector_credentials: OAuth / API token store per tenant per provider ─
    op.create_table(
        "connector_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        # sendgrid | klaviyo | meta_ads | google_ads | webflow | tiktok_ads | shopify
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("credentials", JSONB, nullable=False, server_default=sa.text("'{}'")),
        # Encrypted at rest in prod; for Phase 3 stores: api_key, access_token,
        # refresh_token, account_id, ad_account_id, pixel_id, etc.
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_connector_credentials_tenant_provider", "connector_credentials", ["tenant_id", "provider"])

    # ── connector_jobs: async dispatch tracking ────────────────────────────────
    op.create_table(
        "connector_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("execution_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("execution_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True),
                  sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        # queued | dispatched | delivered | failed | cancelled
        sa.Column("provider_job_id", sa.String(255), nullable=True),
        sa.Column("provider_response", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_connector_jobs_tenant_id", "connector_jobs", ["tenant_id"])
    op.create_index("ix_connector_jobs_execution_run_id", "connector_jobs", ["execution_run_id"])
    op.create_index("ix_connector_jobs_status", "connector_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("connector_jobs")
    op.drop_table("connector_credentials")
