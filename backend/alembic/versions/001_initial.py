"""initial schema + model seed

Revision ID: 001_initial
Revises:
Create Date: 2026-06-30

Creates the 4 Phase 1 tables and seeds the 5 free models (context.md §5.2,
corrected for Groq model deprecations: gpt-oss replaces mixtral and gemma2).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "models",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("cost_per_1k_input", sa.Numeric(10, 6), server_default="0"),
        sa.Column("cost_per_1k_output", sa.Numeric(10, 6), server_default="0"),
        sa.Column("context_window", sa.Integer(), nullable=False),
        sa.Column("speed_tier", sa.String(20), nullable=False),
        sa.Column("best_for", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_models_name", "models", ["name"])

    op.create_table(
        "request_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id"), nullable=False),
        sa.Column("routing_reason", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("original_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_request_logs_api_key_id", "request_logs", ["api_key_id"])
    op.create_index("ix_request_logs_created_at", "request_logs", ["created_at"])

    _seed_models()


def _seed_models() -> None:
    models = sa.table(
        "models",
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("provider", sa.String),
        sa.column("model_id", sa.String),
        sa.column("context_window", sa.Integer),
        sa.column("speed_tier", sa.String),
        sa.column("best_for", postgresql.ARRAY(sa.Text())),
    )
    op.bulk_insert(
        models,
        [
            {
                "name": "llama-3.3-70b-groq",
                "display_name": "Llama 3.3 70B",
                "provider": "groq",
                "model_id": "llama-3.3-70b-versatile",
                "context_window": 128000,
                "speed_tier": "fast",
                "best_for": ["coding", "reasoning", "general"],
            },
            {
                "name": "llama-3.1-8b-groq",
                "display_name": "Llama 3.1 8B",
                "provider": "groq",
                "model_id": "llama-3.1-8b-instant",
                "context_window": 128000,
                "speed_tier": "very_fast",
                "best_for": ["simple", "fast"],
            },
            {
                "name": "gpt-oss-120b-groq",
                "display_name": "GPT-OSS 120B",
                "provider": "groq",
                "model_id": "openai/gpt-oss-120b",
                "context_window": 131072,
                "speed_tier": "fast",
                "best_for": ["math", "analysis"],
            },
            {
                "name": "gpt-oss-20b-groq",
                "display_name": "GPT-OSS 20B",
                "provider": "groq",
                "model_id": "openai/gpt-oss-20b",
                "context_window": 131072,
                "speed_tier": "very_fast",
                "best_for": ["writing", "chat"],
            },
            {
                "name": "qwen-2.5-72b-or",
                "display_name": "Qwen 2.5 72B",
                "provider": "openrouter",
                "model_id": "qwen/qwen-2.5-72b-instruct:free",
                "context_window": 32768,
                "speed_tier": "medium",
                "best_for": ["coding", "math", "reasoning", "analysis"],
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("request_logs")
    op.drop_table("models")
    op.drop_table("api_keys")
    op.drop_table("users")
