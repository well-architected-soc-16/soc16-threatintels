"""buat tabel ip_checks

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ip_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("assessment_status", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("scoring_version", sa.String(length=32), nullable=False),
        sa.Column("coverage", sa.String(length=8), nullable=False),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checked_by", sa.String(length=64), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "assessment_status IN "
            "('COMPLETE', 'DATA_TERBATAS', 'TIDAK_TERSEDIA', 'INPUT_DITOLAK')",
            name=op.f("ck_ip_checks_assessment_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ip_checks")),
    )


def downgrade() -> None:
    op.drop_table("ip_checks")
