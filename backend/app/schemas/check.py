from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer

from app.schemas.common import WibDatetime
from app.services import scoring
from app.services.ip_validation import ReasonCode

AssessmentStatus = Literal["COMPLETE", "DATA_TERBATAS", "TIDAK_TERSEDIA"]
SourceStatus = Literal[
    "OK_SIGNAL", "OK_NO_SIGNAL", "NO_RECORD", "INSUFFICIENT_DATA", "ERROR", "SKIPPED"
]


class CheckCreate(BaseModel):
    ip: str


class SourceResult(BaseModel):
    """Hasil satu sumber. Cek lama hanya menyimpan `source`/`status`/`reason`; field lain
    opsional dan berisi nilai bawaan agar data lama tetap terbaca."""

    source: str
    status: SourceStatus
    # Wajib untuk ERROR dan SKIPPED, null untuk status lain (Bab 3).
    reason: str | None = None
    normalized_score: int | None = None
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    source_time: WibDatetime | None = None
    source_time_type: Literal["last_report", "last_analysis"] | None = None
    retrieved_at: WibDatetime | None = None
    expires_at: WibDatetime | None = None
    from_cache: bool = False
    http_status: int | None = None
    duration_ms: int | None = None
    flags: list[str] = Field(default_factory=list)
    retry_after_seconds: int | None = None


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip: str
    assessment_status: AssessmentStatus
    # Nilai tersimpan berpresisi penuh; hanya respons yang dibulatkan (1 desimal).
    risk_score: float | None
    scoring_version: str
    coverage: str
    flags: list[str]
    sources: list[SourceResult]
    checked_by: str
    checked_at: WibDatetime

    @field_serializer("risk_score")
    def _round_risk_score(self, value: float | None) -> float | None:
        return None if value is None else round(value, 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def indication(self) -> scoring.Indication | None:
        # Dihitung dari nilai tersimpan, bukan yang dibulatkan: 74,96 tampil 75.0 tetapi TINGGI.
        return scoring.indication(self.risk_score)


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
