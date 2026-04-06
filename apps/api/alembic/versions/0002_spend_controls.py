"""Add budget to campaigns and hubspot_list_id to campaign_channels

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Budget cap on campaigns
    op.add_column("campaigns", sa.Column("budget", sa.Numeric(12, 2), nullable=True))
    # HubSpot list ID for email targeting
    op.add_column("campaign_channels", sa.Column("hubspot_list_id", sa.String(100), nullable=True))
    # Retry tracking on execution runs
    op.add_column("execution_runs", sa.Column("retried_from_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("execution_runs", "retried_from_id")
    op.drop_column("campaign_channels", "hubspot_list_id")
    op.drop_column("campaigns", "budget")
