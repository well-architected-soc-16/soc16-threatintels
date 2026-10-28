import enum
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, false, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(enum.StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'analyst', 'viewer')", name="role_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    can_send_misp: Mapped[bool] = mapped_column(Boolean, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
