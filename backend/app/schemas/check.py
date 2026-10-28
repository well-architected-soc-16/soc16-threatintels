from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import WibDatetime
from app.services.ip_validation import ReasonCode

AssessmentStatus = Literal["COMPLETE", "DATA_TERBATAS", "TIDAK_TERSEDIA"]
SourceStatus = Literal[
    "OK_SIGNAL", "OK_NO_SIGNAL", "NO_RECORD", "INSUFFICIENT_DATA", "ERROR", "SKIPPED"
]


class CheckCreate(BaseModel):
    ip: str


class SourceResult(BaseModel):
    source: str
    status: SourceStatus
    reason: str | None = None


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip: str
    assessment_status: AssessmentStatus
    risk_score: float | None
    scoring_version: str
    coverage: str
    flags: list[str]
    sources: list[SourceResult]
    checked_by: str
    checked_at: WibDatetime


class CheckRejected(BaseModel):
    assessment_status: Literal["INPUT_DITOLAK"] = "INPUT_DITOLAK"
    risk_score: None = None
    reason_code: ReasonCode
    message: str


class CheckPage(BaseModel):
    items: list[CheckOut]
    total: int
    limit: int
    offset: int
