"""refresh catalog — qwen3.6 → qwen3.8 on Groq, retire minimax-m3

Revision ID: 009_qwen38_retire_minimax
Revises: 008_reasoning_mode
Create Date: 2026-11-03

check_catalog.py --call on 2026-11-03 found 2 of 8 active models unusable:

  * qwen3.6-27b-groq — `qwen/qwen3.6-27b` no longer listed by Groq. It owned the
    'simple' domain, so every simple-routed request paid a dead hop before
    falling back. Groq now lists `qwen/qwen3.8-27b` (131072 ctx), which takes
    over the slot.
  * minimax-m3-ollama — still listed by Ollama Cloud but HTTP 402 (not in the
    free tier). Owned no domain; it was dead weight at chain position 6.

qwen3.8 does NOT share qwen3.6's dialect. Probed live 2026-11-03: it accepts
none/low/medium/high (3.6 400'd on low), puts reasoning in the sibling
`reasoning` field under reasoning_format=parsed, and never inlined <think>
in content — i.e. 'effort_optional', not 'toggle'.

Retirement is is_active = false, never DELETE (request_logs FKs; see 007).
Net: 7 active models (3 Groq + 4 Ollama), every domain still claimed.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_qwen38_retire_minimax"
down_revision = "008_reasoning_mode"
branch_labels = None
depends_on = None

_RETIRED = ["qwen3.6-27b-groq", "minimax-m3-ollama"]

_NEW = {
    "name": "qwen3.8-27b-groq",
    "display_name": "Qwen3.8 27B",
    "provider": "groq",
    "model_id": "qwen/qwen3.8-27b",
    "context_window": 131072,
    "speed_tier": "fast",
    "best_for": ["simple", "general"],
    "reasoning_mode": "effort_optional",
}

# (name, fallback_priority, routing_domains) for the 7 active models.
_ACTIVE = [
    ("gpt-oss-120b-groq", 0, ["coding", "math"]),
    ("qwen3.8-27b-groq", 1, ["simple"]),
    ("gpt-oss-20b-groq", 2, ["general"]),
    ("nemotron-3-nano-ollama", 3, []),
    ("nemotron-3-ultra-ollama", 4, ["analysis"]),
    ("nemotron-3-super-ollama", 5, []),
    ("gemma4-31b-ollama", 6, ["writing"]),
]

# 007's _ACTIVE, restored by downgrade().
_PRIOR = [
    ("gpt-oss-120b-groq", 0, ["coding", "math"]),
    ("qwen3.6-27b-groq", 1, ["simple"]),
    ("gpt-oss-20b-groq", 2, ["general"]),
    ("nemotron-3-nano-ollama", 3, []),
    ("nemotron-3-ultra-ollama", 4, ["analysis"]),
    ("nemotron-3-super-ollama", 5, []),
    ("minimax-m3-ollama", 6, []),
    ("gemma4-31b-ollama", 7, ["writing"]),
]

_MODELS = sa.table(
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
    sa.column("reasoning_mode", sa.String),
)


def _set_active(names: list[str], active: bool) -> None:
    op.execute(_MODELS.update().where(_MODELS.c.name.in_(names)).values(is_active=active))


def _apply_routing(rows: list[tuple[str, int, list[str]]]) -> None:
    for name, priority, domains in rows:
        op.execute(
            _MODELS.update()
            .where(_MODELS.c.name == name)
            .values(fallback_priority=priority, routing_domains=domains)
        )


def upgrade() -> None:
    _set_active(_RETIRED, False)
    op.bulk_insert(
        _MODELS, [{**_NEW, "is_active": True, "routing_domains": [], "fallback_priority": 0}]
    )
    _apply_routing(_ACTIVE)


def downgrade() -> None:
    # Delete the new row only if it has no request history (FKs), else deactivate.
    op.execute(
        sa.text(
            "DELETE FROM models WHERE name = :name AND id NOT IN ("
            "  SELECT model_id FROM request_logs"
            "  UNION SELECT original_model_id FROM request_logs WHERE original_model_id IS NOT NULL"
            ")"
        ).bindparams(name=_NEW["name"])
    )
    _set_active([_NEW["name"]], False)
    _set_active(_RETIRED, True)
    _apply_routing(_PRIOR)
