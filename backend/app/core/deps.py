from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Role, User
from app.services import audit

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise _unauthorized("Token tidak valid atau kedaluwarsa") from None

    # Role dan status akun selalu dibaca ulang dari DB; klaim di token tidak dipercaya.
    user = db.scalar(select(User).where(User.username == payload["sub"]))
    if user is None:
        raise _unauthorized("Token tidak valid atau kedaluwarsa")
    if not user.is_active:
        raise _unauthorized("Akun nonaktif")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _deny(request: Request, db: Session, user: User, required: dict) -> HTTPException:
    audit.record(
        db,
        action="access_denied",
        result="denied",
        actor_username=user.username,
        target=f"{request.method} {request.url.path}",
        detail=required,
        ip_address=audit.client_ip(request),
    )
    # Commit di sini: HTTPException membatalkan transaksi request, tetapi
    # catatan penolakan harus tetap tersimpan.
    db.commit()
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")


def require_roles(*roles: Role) -> Callable[..., User]:
    allowed = {role.value for role in roles}

    def dependency(request: Request, user: CurrentUser, db: DbSession) -> User:
        if user.role not in allowed:
            raise _deny(request, db, user, {"required_roles": sorted(allowed)})
        return user

    return dependency


def require_misp_permission(request: Request, user: CurrentUser, db: DbSession) -> User:
    """Admin, atau analyst dengan can_send_misp. Viewer selalu ditolak."""
    is_admin = user.role == Role.ADMIN
    is_misp_analyst = user.role == Role.ANALYST and user.can_send_misp
    if not (is_admin or is_misp_analyst):
        raise _deny(
            request, db, user, {"required": "admin atau analyst dengan can_send_misp"}
        )
    return user
