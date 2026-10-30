from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceCache(Base):
    """Cache hasil per sumber. Hanya status yang boleh di-cache; ERROR, INSUFFICIENT_DATA, dan
    SKIPPED tidak pernah disimpan (CHECK di bawah menjaganya di level DB)."""

    __tablename__ = "source_cache"
    __table_args__ = (
        UniqueConstraint("source", "ip", "params_key", "mode"),
        CheckConstraint("mode IN ('mock', 'live')", name="mode_valid"),
        CheckConstraint(
            "status IN ('OK_SIGNAL', 'OK_NO_SIGNAL', 'NO_RECORD')",
            name="status_cacheable",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    ip: Mapped[str] = mapped_column(String(45))
    # Parameter yang mengubah hasil: AbuseIPDB "maxAgeInDays=30"; VirusTotal "".
    params_key: Mapped[str] = mapped_column(String(64))
    # Mode live tidak pernah membaca baris mock (dan sebaliknya).
    mode: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24))
    normalized_score: Mapped[int | None] = mapped_column(Integer)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Flag per sumber (NO_VENDOR_OPINION, SUMBER_SIMULASI). Tanpa kolom ini, hasil dari cache
    # kehilangan SUMBER_SIMULASI dan lolos dari guard MISP.
    flags: Mapped[list[str]] = mapped_column(JSONB)
    source_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_time_type: Mapped[str | None] = mapped_column(String(16))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
