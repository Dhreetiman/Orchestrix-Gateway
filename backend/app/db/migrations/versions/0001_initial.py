"""initial schema: api_keys, request_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("streamed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"], ["api_keys.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_request_logs_provider", "request_logs", ["provider"])
    op.create_index("ix_request_logs_model", "request_logs", ["model"])
    op.create_index("ix_request_logs_prompt_hash", "request_logs", ["prompt_hash"])
    op.create_index("ix_request_logs_status", "request_logs", ["status"])
    op.create_index("ix_request_logs_cache_hit", "request_logs", ["cache_hit"])
    op.create_index("ix_request_logs_created_at", "request_logs", ["created_at"])
    op.create_index(
        "ix_request_logs_provider_created", "request_logs", ["provider", "created_at"]
    )
    op.create_index("ix_request_logs_model_created", "request_logs", ["model", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_request_logs_model_created", table_name="request_logs")
    op.drop_index("ix_request_logs_provider_created", table_name="request_logs")
    op.drop_index("ix_request_logs_created_at", table_name="request_logs")
    op.drop_index("ix_request_logs_cache_hit", table_name="request_logs")
    op.drop_index("ix_request_logs_status", table_name="request_logs")
    op.drop_index("ix_request_logs_prompt_hash", table_name="request_logs")
    op.drop_index("ix_request_logs_model", table_name="request_logs")
    op.drop_index("ix_request_logs_provider", table_name="request_logs")
    op.drop_table("request_logs")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
