from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    verify_password,
)
from app.models import User
from app.schemas.common import UNAUTHORIZED, ErrorResponse
from app.schemas.user import Token, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"model": ErrorResponse, "description": "Username atau password salah"}
    },
)
def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    user = db.scalar(select(User).where(User.username == form.username))
    # Selalu verifikasi, bahkan saat user tidak ada, agar waktu respons seragam.
    password_ok = verify_password(
        form.password, user.password_hash if user else DUMMY_HASH
    )

    if user is None or not password_ok or not user.is_active:
        reason = (
            "user_tidak_ada"
            if user is None
            else "password_salah"
            if not password_ok
            else "akun_nonaktif"
        )
        audit.record(
            db,
            action="login",
            result="denied",
            # Pelaku belum terautentikasi; username yang dicoba disimpan di detail.
            detail={"username": form.username[:64], "reason": reason},
            ip_address=audit.client_ip(request),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    audit.record(
        db,
        action="login",
        result="success",
        actor_username=user.username,
        ip_address=audit.client_ip(request),
    )
    db.commit()
    return Token(access_token=create_access_token(user.username, user.role))


@router.get("/me", response_model=UserOut, responses=UNAUTHORIZED)
def me(user: CurrentUser) -> User:
    return user
