from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def record(
    db: Session,
    *,
    action: str,
    result: str,
    actor_username: str | None = None,
    target: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Tambahkan satu baris audit ke session. Pemanggil yang melakukan commit,
    sehingga audit ikut atomik dengan perubahan yang dicatat.

    `detail` TIDAK BOLEH berisi password, token, atau API key.
    """
    db.add(
        AuditLog(
            actor_username=actor_username,
            action=action,
            target=target,
            result=result,
            detail=detail,
            ip_address=ip_address,
        )
    )
