"""Add experiment engine — experiments table, traffic_weight on variants, variant_id on events

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── content_variants: add traffic weight for A/B splitting ────────────────
    op.add_column(
        "content_variants",
        sa.Column("traffic_weight", sa.Float(), nullable=False, server_default="1.0"),
    )

    # ── analytics_events: add variant_id for per-variant event tracking ───────
    op.add_column(
        "analytics_events",
        sa.Column(
            "variant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("content_variants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_analytics_events_variant_id", "analytics_events", ["variant_id"])

    # ── experiments table ─────────────────────────────────────────────────────
    op.create_table(
        "experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.95"),
        sa.Column("winner_variant_id", UUID(as_uuid=True), sa.ForeignKey("content_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("auto_promote", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_experiments_tenant_id", "experiments", ["tenant_id"])
    op.create_index("ix_experiments_campaign_id", "experiments", ["campaign_id"])
    op.create_index("ix_experiments_asset_id", "experiments", ["asset_id"])


def downgrade() -> None:
    op.drop_table("experiments")
    op.drop_index("ix_analytics_events_variant_id", table_name="analytics_events")
    op.drop_column("analytics_events", "variant_id")
    op.drop_column("content_variants", "traffic_weight")
