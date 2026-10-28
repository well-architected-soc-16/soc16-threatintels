from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import Role
from app.schemas.common import WibDatetime

Username = Annotated[
    str, StringConstraints(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    can_send_misp: bool
    is_active: bool
    created_at: WibDatetime
    updated_at: WibDatetime


class UserCreate(BaseModel):
    username: Username
    password: Annotated[str, Field(min_length=12, max_length=128)]
    role: Role
    can_send_misp: bool = False


class UserUpdate(BaseModel):
    role: Role | None = None
    can_send_misp: bool | None = None
    is_active: bool | None = None
