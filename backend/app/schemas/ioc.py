from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import WibDatetime

Reason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
]
Tag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


class IocSubmit(BaseModel):
    check_id: int
    reason: Reason
    tags: Annotated[list[Tag], Field(max_length=20)] = []


class IocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    check_id: int
    ip: str
    reason: str
    tags: list[str]
    status: Literal["pending", "mock_sent", "sent", "failed"]
    misp_event_uuid: str | None
    error_message: str | None
    submitted_by: str
    submitted_at: WibDatetime


class IocPage(BaseModel):
    items: list[IocOut]
    total: int
    limit: int
    offset: int


class IocDuplicate(BaseModel):
    detail: str
    submission_id: int
