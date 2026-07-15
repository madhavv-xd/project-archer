"""admin role + DB-driven routing config

Revision ID: 006_admin_and_routing_config
Revises: 005_embedding_routing
Create Date: 2026-07-15

Phase 2E (openspec/changes/phase-2e-admin-panel):
- users.role ('user' | 'admin'). No signup path grants admin — promote via a
  manual UPDATE on Neon.
- models.routing_domains TEXT[] + models.fallback_priority INTEGER move the
  domain->model map (was hardcoded across router.py / embeddings.py) and the
  fallback order (was proxy.py's FALLBACK_CHAIN list) into the DB, read by the
  in-memory ModelCache. Retires the Phase-2A three-file-sync rule.

The backfill reproduces the pre-2E hardcoded behavior VERBATIM (fallback order =
the old FALLBACK_CHAIN, domains = router.py/DOMAIN_MODEL targets), so the cutover
is invisible to live routing. Chains after 005_embedding_routing (current head).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "006_admin_and_routing_config"
down_revision = "005_embedding_routing"
branch_labels = None
depends_on = None

# (name, fallback_priority, routing_domains) — verbatim from the old
# proxy.FALLBACK_CHAIN order and the router.py / embeddings.DOMAIN_MODEL targets.
_BACKFILL = [
    ("llama-3.3-70b-groq", 0, ["coding", "general"]),
    ("llama-4-scout-groq", 1, ["writing"]),
    ("gpt-oss-120b-groq", 2, ["math"]),
    ("qwen3-coder-ollama", 3, []),
    ("nemotron-3-super-ollama", 4, ["analysis"]),
    ("minimax-m3-ollama", 5, []),
    ("glm-4.7-ollama", 6, []),
    ("gpt-oss-20b-groq", 7, []),
    ("llama-3.1-8b-groq", 8, ["simple"]),
]

_models = sa.table(
    "models",
    sa.column("name", sa.String),
    sa.column("routing_domains", postgresql.ARRAY(sa.Text())),
    sa.column("fallback_priority", sa.Integer),
)


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("role", sa.String(20), server_default="user", nullable=False)
    )
    op.add_column(
        "models",
        sa.Column(
            "routing_domains", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
    )
    op.add_column("models", sa.Column("fallback_priority", sa.Integer()))

    for name, priority, domains in _BACKFILL:
        op.execute(
            _models.update()
            .where(_models.c.name == name)
            .values(fallback_priority=priority, routing_domains=domains)
        )

    # Every seeded model is backfilled above, so the column can now be NOT NULL.
    op.alter_column("models", "fallback_priority", nullable=False)


def downgrade() -> None:
    op.drop_column("models", "fallback_priority")
    op.drop_column("models", "routing_domains")
    op.drop_column("users", "role")
