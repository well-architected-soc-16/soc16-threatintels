from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IocSubmission(Base):
    __tablename__ = "ioc_submissions"
    __table_args__ = (
        CheckConstraint("char_length(reason) >= 10", name="reason_min_length"),
        CheckConstraint(
            "status IN ('pending', 'mock_sent', 'sent', 'failed')",
            name="status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # UNIQUE: satu check hanya punya satu submission, jadi klik ulang tidak menggandakan.
    check_id: Mapped[int] = mapped_column(ForeignKey("ip_checks.id"), unique=True)
    ip: Mapped[str] = mapped_column(String(45))
    reason: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    misp_event_uuid: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str] = mapped_column(String(64))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
