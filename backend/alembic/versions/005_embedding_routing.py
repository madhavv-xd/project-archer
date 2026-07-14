"""embedding routing columns

Revision ID: 005_embedding_routing
Revises: 003_expand_catalog
Create Date: 2026-07-14

Phase 2B (openspec/changes/phase-2b-embedding-routing): records which engine
decided each request (routing_method) and, in shadow mode, what the embedding
router would have chosen (shadow_routing_reason, nullable). Additive/defaulted —
2A code runs fine against the new schema before 2B app code deploys. Chains
after 003_expand_catalog (the current head).
"""

import sqlalchemy as sa
from alembic import op

revision = "005_embedding_routing"
down_revision = "003_expand_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("routing_method", sa.String(20), server_default="keyword", nullable=False),
    )
    op.add_column("request_logs", sa.Column("shadow_routing_reason", sa.String(100)))


def downgrade() -> None:
    op.drop_column("request_logs", "shadow_routing_reason")
    op.drop_column("request_logs", "routing_method")
