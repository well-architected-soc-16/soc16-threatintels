from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.timeutil import now_wib_iso
from app.db.session import check_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "error"]
    misp_mode: Literal["mock", "live"]
    time: str


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "Database tidak dapat dijangkau"}
    },
)
def health() -> HealthResponse | JSONResponse:
    db_ok = check_db()
    body = HealthResponse(
        status="ok" if db_ok else "degraded",
        db="ok" if db_ok else "error",
        misp_mode=get_settings().misp_mode,
        time=now_wib_iso(),
    )
    if db_ok:
        return body
    return JSONResponse(status_code=503, content=body.model_dump())
