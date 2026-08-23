"""add models.reasoning_mode — per-model chain-of-thought capability

Revision ID: 008_reasoning_mode
Revises: 007_refresh_catalog
Create Date: 2026-08-24

openspec/changes/phase-2h-playground-reasoning.

Archer promises one answer shape whichever model served the request, but the
providers disagree about reasoning in two incompatible ways, both verified live
against this project's keys on 2026-08-24:

  * WHERE it goes — most models return it in a sibling `message.reasoning`
    field, but qwen/qwen3.6-27b inlines it in `content` as `<think>...</think>`,
    which is what was leaking a visible scratchpad into playground replies.
  * WHAT effort vocabulary they accept — openai/gpt-oss-* take low/medium/high
    and reject `none`; qwen3.6 takes none/default and rejects `low`. A wrong
    value is HTTP 400, which providers/base.py categorizes `client_error` — and
    client errors are deliberately NOT retried, so it fails the request outright
    rather than falling back.

Deriving that from the model name in code is exactly the coupling Phase 2E's
DB-driven catalog removed, and the catalog historically loses ~5 of 9 models per
refresh, so it goes in a column. Default 'none' (send no reasoning parameters)
is the conservative value: an unverified model degrades to "reasoning not
suppressed", never to failed requests.
"""

import sqlalchemy as sa
from alembic import op

revision = "008_reasoning_mode"
down_revision = "007_refresh_catalog"
branch_labels = None
depends_on = None

# (model name, mode) for the 8 models active as of 007. Probe with
# `uv run python probe_reasoning.py` after any catalog change.
_MODES = [
    # Groq gpt-oss: reasoning always happens; only its verbosity is dialable, and
    # reasoning_format=hidden is what keeps it out of the answer.
    ("gpt-oss-120b-groq", "effort"),
    ("gpt-oss-20b-groq", "effort"),
    # Groq qwen3.6: the inline-<think> offender. none/default only.
    ("qwen3.6-27b-groq", "toggle"),
    # Ollama nemotron/minimax: honor `none`, and grade effort.
    ("nemotron-3-nano-ollama", "effort_optional"),
    ("nemotron-3-ultra-ollama", "effort_optional"),
    ("nemotron-3-super-ollama", "effort_optional"),
    ("minimax-m3-ollama", "effort_optional"),
    # gemma4 does not reason on its own — but it STARTS reasoning if sent an
    # effort parameter at all, so 'none' here means "send nothing", not "off".
    ("gemma4-31b-ollama", "none"),
]


def upgrade() -> None:
    op.add_column(
        "models",
        sa.Column("reasoning_mode", sa.String(20), server_default="none", nullable=False),
    )
    for name, mode in _MODES:
        op.execute(
            sa.text("UPDATE models SET reasoning_mode = :mode WHERE name = :name").bindparams(
                mode=mode, name=name
            )
        )


def downgrade() -> None:
    op.drop_column("models", "reasoning_mode")
