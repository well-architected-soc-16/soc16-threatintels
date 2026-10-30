from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceCall(Base):
    """Log setiap request keluar ke sumber: bukti sekaligus dasar hitung kuota.

    Tanpa key, header, maupun body. Baris dibuat SEBELUM request dikirim (reservasi), jadi
    baris yang tidak pernah diselesaikan (`result_status` NULL) tetap dihitung sebagai pemakaian.
    Hanya `mode = 'live'` yang dihitung limiter; panggilan mock dicatat sebagai bukti saja.
    """

    __tablename__ = "source_calls"
    __table_args__ = (
        CheckConstraint("mode IN ('mock', 'live')", name="mode_valid"),
        Index("ix_source_calls_lookup", "source", "mode", "called_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(8))
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    result_status: Mapped[str | None] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(String(32))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer)
    # Header X-RateLimit-* dari respons (AbuseIPDB); dasar reset harian dan bukti sisa kuota.
    rate_limit_reset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rate_limit_remaining: Mapped[int | None] = mapped_column(Integer)
