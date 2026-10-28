"""buat tabel ioc_submissions

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ioc_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("check_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("misp_event_uuid", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.String(length=64), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(reason) >= 10",
            name=op.f("ck_ioc_submissions_reason_min_length"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'mock_sent', 'sent', 'failed')",
            name=op.f("ck_ioc_submissions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["ip_checks.id"],
            name=op.f("fk_ioc_submissions_check_id_ip_checks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ioc_submissions")),
        sa.UniqueConstraint("check_id", name=op.f("uq_ioc_submissions_check_id")),
    )


def downgrade() -> None:
    op.drop_table("ioc_submissions")
