"""phase 2a columns

Revision ID: 004_phase2a_columns
Revises: 002_add_oauth
Create Date: 2026-07-06

Phase 2A schema additions (openspec/changes/phase-2a-streaming-limits-catalog):
users.plan for plan-based rate limits, request_logs streaming telemetry
(is_streaming, time_to_first_token_ms), and the composite index for dashboard
aggregates. NOTE: ix_request_logs_created_at already exists from 001_initial,
so only the composite (api_key_id, created_at) index is added here. This
migration precedes 003_expand_catalog in the chain (columns shipped first).
"""

import sqlalchemy as sa
from alembic import op

revision = "004_phase2a_columns"
down_revision = "002_add_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(20), server_default="free", nullable=False),
    )
    op.add_column(
        "request_logs",
        sa.Column("is_streaming", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("request_logs", sa.Column("time_to_first_token_ms", sa.Integer()))
    op.create_index(
        "ix_request_logs_api_key_created", "request_logs", ["api_key_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_request_logs_api_key_created", table_name="request_logs")
    op.drop_column("request_logs", "time_to_first_token_ms")
    op.drop_column("request_logs", "is_streaming")
    op.drop_column("users", "plan")
