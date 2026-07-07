"""rebalance model catalog 5 -> 9 (Phase 2A)

Revision ID: 003_expand_catalog
Revises: 004_phase2a_columns
Create Date: 2026-07-07

Phase 2A catalog work (openspec/changes/phase-2a-streaming-limits-catalog).
Verified live against the Groq / Ollama Cloud lineups at implementation time
(2026-07-07):

  REMOVE the OpenRouter :free model seeded by 001 — it is chronically HTTP 429
  under real use (unreliable), and Ollama Cloud now provides reliable large-model
  coverage instead. (OpenRouter provider code stays for future use.)

  ADD 5 free, OpenAI-compatible, streaming-capable models filling the thin
  writing / long-context / reasoning domains:
    - llama-4-scout-groq       (Groq, fast, 131k)   general/writing, reliable
    - qwen3-coder-ollama       (Ollama, 262k)       coding + long context
    - glm-4.7-ollama           (Ollama, 203k)       general/writing
    - minimax-m3-ollama        (Ollama, 524k)       general + very long context
    - nemotron-3-super-ollama  (Ollama, 262k)       reasoning/analysis

Net: 4 Groq (from 001) + these 5 = 9 active models. The NAMES here are kept in
sync with app/core/router.py and app/core/proxy.py (enforced by
tests/test_catalog_sync.py). Chains AFTER 004_phase2a_columns (columns first).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_expand_catalog"
down_revision = "004_phase2a_columns"
branch_labels = None
depends_on = None

# Removed: the flaky OpenRouter :free model seeded by 001_initial.
_REMOVED_NAMES = ["qwen-2.5-72b-or"]

_NEW_MODELS = [
    {
        "name": "llama-4-scout-groq",
        "display_name": "Llama 4 Scout 17B",
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "context_window": 131072,
        "speed_tier": "fast",
        "best_for": ["writing", "general", "long-context"],
    },
    {
        "name": "qwen3-coder-ollama",
        "display_name": "Qwen3 Coder 480B",
        "provider": "ollama",
        "model_id": "qwen3-coder:480b",
        "context_window": 262144,
        "speed_tier": "medium",
        "best_for": ["coding", "long-context"],
    },
    {
        "name": "glm-4.7-ollama",
        "display_name": "GLM 4.7",
        "provider": "ollama",
        "model_id": "glm-4.7",
        "context_window": 202752,
        "speed_tier": "medium",
        "best_for": ["general", "writing"],
    },
    {
        "name": "minimax-m3-ollama",
        "display_name": "MiniMax M3",
        "provider": "ollama",
        "model_id": "minimax-m3",
        "context_window": 524288,
        "speed_tier": "medium",
        "best_for": ["general", "analysis", "long-context"],
    },
    {
        "name": "nemotron-3-super-ollama",
        "display_name": "Nemotron 3 Super",
        "provider": "ollama",
        "model_id": "nemotron-3-super",
        "context_window": 262144,
        "speed_tier": "medium",
        "best_for": ["reasoning", "analysis"],
    },
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
)


def _delete_by_name(names: list[str]) -> None:
    op.execute(
        sa.text("DELETE FROM models WHERE name IN :names").bindparams(
            sa.bindparam("names", value=tuple(names), expanding=True)
        )
    )


def upgrade() -> None:
    _delete_by_name(_REMOVED_NAMES)
    op.bulk_insert(_MODELS_TABLE, _NEW_MODELS)


def downgrade() -> None:
    _delete_by_name([m["name"] for m in _NEW_MODELS])
    # Restore the OpenRouter model removed on upgrade (matches 001_initial seed).
    op.bulk_insert(
        _MODELS_TABLE,
        [
            {
                "name": "qwen-2.5-72b-or",
                "display_name": "Qwen 2.5 72B",
                "provider": "openrouter",
                "model_id": "qwen/qwen-2.5-72b-instruct:free",
                "context_window": 32768,
                "speed_tier": "medium",
                "best_for": ["coding", "math", "reasoning", "analysis"],
            }
        ],
    )
