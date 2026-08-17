"""refresh model catalog — retire 5 decommissioned models, seed 4 live ones

Revision ID: 007_refresh_catalog
Revises: 006_admin_and_routing_config
Create Date: 2026-08-18

openspec/changes/refresh-model-catalog.

The 2A catalog was verified live on 2026-07-07. Re-verified 2026-08-18 against
Groq's and Ollama Cloud's model listings: 5 of the 9 seeded models no longer
exist upstream. Because they were still is_active, ModelCache kept ranking them
— so the priority-0 default was dead (a wasted provider round-trip on every
coding/general request) and the only 'writing' and 'simple' models were dead
(those routing decisions silently discarded).

Retirement is is_active = false, NOT delete: request_logs.model_id and
.original_model_id are FKs to models.id with no ondelete, so deleting a model
with history raises a ForeignKeyViolation. ModelCache.load() already filters on
is_active, so an inactive row is invisible to routing and fallback while its
historical logs keep valid references. This is the same mechanism the 2E admin
panel's model toggle uses.

Replacements were chosen by smoke-testing real chat completions on this
project's free-tier keys, not from provider docs — most of Ollama Cloud's
current lineup (deepseek-v4-*, glm-5.x, kimi-*, qwen3.5:397b,
mistral-large-3:675b, minimax-m2.7) returns HTTP 403 subscription required.

Net: 8 active models (3 Groq + 5 Ollama), every routing domain claimed by
exactly one live model, chain ordered fastest-first with Groq at the head.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007_refresh_catalog"
down_revision = "006_admin_and_routing_config"
branch_labels = None
depends_on = None

# Decommissioned upstream — deactivated, not deleted (see docstring).
_RETIRED = [
    "llama-3.3-70b-groq",
    "llama-4-scout-groq",
    "qwen3-coder-ollama",
    "glm-4.7-ollama",
    "llama-3.1-8b-groq",
]

_NEW_MODELS = [
    {
        "name": "qwen3.6-27b-groq",
        "display_name": "Qwen3.6 27B",
        "provider": "groq",
        "model_id": "qwen/qwen3.6-27b",
        "context_window": 131072,
        "speed_tier": "fast",
        "best_for": ["simple", "general"],
    },
    {
        "name": "nemotron-3-ultra-ollama",
        "display_name": "Nemotron 3 Ultra",
        "provider": "ollama",
        "model_id": "nemotron-3-ultra",
        "context_window": 262144,
        "speed_tier": "medium",
        "best_for": ["analysis", "reasoning"],
    },
    {
        "name": "nemotron-3-nano-ollama",
        "display_name": "Nemotron 3 Nano 30B",
        "provider": "ollama",
        "model_id": "nemotron-3-nano:30b",
        "context_window": 131072,
        "speed_tier": "fast",
        "best_for": ["general", "simple"],
    },
    {
        "name": "gemma4-31b-ollama",
        "display_name": "Gemma 4 31B",
        "provider": "ollama",
        "model_id": "gemma4:31b",
        "context_window": 131072,
        "speed_tier": "slow",
        "best_for": ["writing", "general"],
    },
]

# (name, fallback_priority, routing_domains) for the 8 active models.
# Groq holds 0-2 (faster + not concurrency-capped on the free tier); the slowest
# model sits last. Domain ownership is independent of chain position — gemma4 is
# the deliberate 'writing' choice but is never an early fallback for others.
_ACTIVE = [
    ("gpt-oss-120b-groq", 0, ["coding", "math"]),
    ("qwen3.6-27b-groq", 1, ["simple"]),
    ("gpt-oss-20b-groq", 2, ["general"]),
    ("nemotron-3-nano-ollama", 3, []),
    ("nemotron-3-ultra-ollama", 4, ["analysis"]),
    ("nemotron-3-super-ollama", 5, []),
    ("minimax-m3-ollama", 6, []),
    ("gemma4-31b-ollama", 7, ["writing"]),
]

# Pre-007 state, restored by downgrade() (verbatim from 006's backfill).
_PRIOR = [
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

_MODELS_TABLE = sa.table(
    "models",
    sa.column("name", sa.String),
    sa.column("display_name", sa.String),
    sa.column("provider", sa.String),
    sa.column("model_id", sa.String),
    sa.column("context_window", sa.Integer),
    sa.column("speed_tier", sa.String),
    sa.column("best_for", postgresql.ARRAY(sa.Text())),
    sa.column("is_active", sa.Boolean),
    sa.column("routing_domains", postgresql.ARRAY(sa.Text())),
    sa.column("fallback_priority", sa.Integer),
)


def _set_active(names: list[str], active: bool) -> None:
    op.execute(
        _MODELS_TABLE.update()
        .where(_MODELS_TABLE.c.name.in_(names))
        .values(is_active=active)
    )


def _apply_routing(rows: list[tuple[str, int, list[str]]]) -> None:
    for name, priority, domains in rows:
        op.execute(
            _MODELS_TABLE.update()
            .where(_MODELS_TABLE.c.name == name)
            .values(fallback_priority=priority, routing_domains=domains)
        )


def upgrade() -> None:
    _set_active(_RETIRED, False)
    # Retired rows keep their stale priorities/domains — harmless, since
    # ModelCache.load() filters on is_active before sorting or building the
    # domain map.
    op.bulk_insert(
        _MODELS_TABLE,
        [{**m, "is_active": True, "routing_domains": [], "fallback_priority": 0} for m in _NEW_MODELS],
    )
    _apply_routing(_ACTIVE)


def downgrade() -> None:
    # The new rows may have accumulated request_logs by now; delete them only if
    # they have none, otherwise just deactivate. Keeps `alembic downgrade base`
    # (the documented dev reset) working without a FK violation.
    new_names = [m["name"] for m in _NEW_MODELS]
    op.execute(
        sa.text(
            "DELETE FROM models WHERE name IN :names AND id NOT IN ("
            "  SELECT model_id FROM request_logs"
            "  UNION SELECT original_model_id FROM request_logs WHERE original_model_id IS NOT NULL"
            ")"
        ).bindparams(sa.bindparam("names", value=tuple(new_names), expanding=True))
    )
    _set_active(new_names, False)
    _set_active(_RETIRED, True)
    _apply_routing(_PRIOR)
