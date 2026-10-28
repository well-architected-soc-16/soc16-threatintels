from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

from app.core.timeutil import to_wib_iso

# Disimpan UTC, dikirim ke klien sebagai ISO 8601 dengan offset WIB (+07:00).
WibDatetime = Annotated[
    datetime, PlainSerializer(to_wib_iso, return_type=str, when_used="json")
]


class ErrorResponse(BaseModel):
    detail: str


UNAUTHORIZED = {
    401: {
        "model": ErrorResponse,
        "description": "Token tidak ada, rusak, kedaluwarsa, atau akun nonaktif",
    }
}
FORBIDDEN = {403: {"model": ErrorResponse, "description": "Role tidak memiliki izin"}}
