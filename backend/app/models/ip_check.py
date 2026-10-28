from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IpCheck(Base):
    __tablename__ = "ip_checks"
    __table_args__ = (
        CheckConstraint(
            "assessment_status IN "
            "('COMPLETE', 'DATA_TERBATAS', 'TIDAK_TERSEDIA', 'INPUT_DITOLAK')",
            name="assessment_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(45))
    assessment_status: Mapped[str] = mapped_column(String(16))
    # NULL berarti tidak dapat dinilai. Error/data kosong tidak boleh jadi 0.
    risk_score: Mapped[float | None] = mapped_column(Float)
    scoring_version: Mapped[str] = mapped_column(String(32))
    # Jumlah sumber yang bisa dinilai dari total, mis. "0/2".
    coverage: Mapped[str] = mapped_column(String(8))
    flags: Mapped[list[str]] = mapped_column(JSONB)
    # Hasil per sumber: [{"source", "status", "reason"}, ...].
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    checked_by: Mapped[str] = mapped_column(String(64))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
