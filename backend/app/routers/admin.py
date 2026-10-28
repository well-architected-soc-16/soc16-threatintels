from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import DbSession, require_roles
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.common import FORBIDDEN, UNAUTHORIZED, ErrorResponse
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import audit

AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={**UNAUTHORIZED, **FORBIDDEN},
)


@router.get("/users", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse, "description": "Username sudah dipakai"}},
)
def create_user(
    body: UserCreate, request: Request, admin: AdminUser, db: DbSession
) -> User:
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role.value,
        can_send_misp=body.can_send_misp,
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username sudah dipakai"
        ) from None

    audit.record(
        db,
        action="user_create",
        result="success",
        actor_username=admin.username,
        target=user.username,
        detail={"role": user.role, "can_send_misp": user.can_send_misp},
        ip_address=audit.client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    responses={
        404: {"model": ErrorResponse, "description": "User tidak ditemukan"},
        409: {
            "model": ErrorResponse,
            "description": "Admin tidak boleh menurunkan atau menonaktifkan dirinya sendiri",
        },
    },
)
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    admin: AdminUser,
    db: DbSession,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan"
        )

    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    new_role = changes.get("role")
    if user.id == admin.id and (
        (new_role is not None and new_role != Role.ADMIN)
        or changes.get("is_active") is False
    ):
        # Mencegah admin terkunci keluar dari sistemnya sendiri.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin tidak boleh menurunkan atau menonaktifkan dirinya sendiri",
        )

    diff: dict[str, list] = {}
    for field, value in changes.items():
        value = value.value if isinstance(value, Role) else value
        old = getattr(user, field)
        if old != value:
            diff[field] = [old, value]
            setattr(user, field, value)

    audit.record(
        db,
        action="user_update",
        result="success",
        actor_username=admin.username,
        target=user.username,
        detail={"changes": diff},
        ip_address=audit.client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user
