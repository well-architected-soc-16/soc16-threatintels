"""buat tabel source_cache dan source_calls

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("params_key", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("normalized_score", sa.Integer(), nullable=True),
        sa.Column(
            "evidence_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_time_type", sa.String(length=16), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('mock', 'live')", name=op.f("ck_source_cache_mode_valid")
        ),
        sa.CheckConstraint(
            "status IN ('OK_SIGNAL', 'OK_NO_SIGNAL', 'NO_RECORD')",
            name=op.f("ck_source_cache_status_cacheable"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_cache")),
        sa.UniqueConstraint(
            "source", "ip", "params_key", "mode", name=op.f("uq_source_cache_source")
        ),
    )
    op.create_table(
        "source_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("result_status", sa.String(length=24), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_after_seconds", sa.Integer(), nullable=True),
        sa.Column("rate_limit_reset", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_remaining", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "mode IN ('mock', 'live')", name=op.f("ck_source_calls_mode_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_calls")),
    )
    op.create_index(
        "ix_source_calls_lookup",
        "source_calls",
        ["source", "mode", "called_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_calls_lookup", table_name="source_calls")
    op.drop_table("source_calls")
    op.drop_table("source_cache")
