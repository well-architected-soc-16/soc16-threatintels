"""Kontrak adapter sumber reputasi (TASK-02 Tahap 1).

Hanya tipe dan Protocol; tidak ada I/O. Pemetaan status mengikuti Bab 3 dokumen riset tim.
Hanya `OK_SIGNAL` dan `OK_NO_SIGNAL` yang membawa `normalized_score`; status lain selalu null
(error/kosong TIDAK BOLEH diubah menjadi skor 0).
`reason` wajib diisi untuk `ERROR` dan `SKIPPED` (Bab 3: "SKIPPED; nilai null; sertakan alasan")
dan harus null untuk status lain; aturan ini ditegakkan di `SourceResult.__post_init__`.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol


class SourceStatus(enum.StrEnum):
    OK_SIGNAL = "OK_SIGNAL"
    OK_NO_SIGNAL = "OK_NO_SIGNAL"
    NO_RECORD = "NO_RECORD"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


# Status yang boleh membawa skor dan menambah cakupan (coverage).
SCORED_STATUSES = frozenset({SourceStatus.OK_SIGNAL, SourceStatus.OK_NO_SIGNAL})


# Status yang wajib menyertakan `reason`; status lain wajib `reason=None`.
REASON_REQUIRED_STATUSES = frozenset({SourceStatus.ERROR, SourceStatus.SKIPPED})


class SourceReason(enum.StrEnum):
    """Alasan untuk status ERROR atau SKIPPED (= `error_code` di kontrak API)."""

    # ERROR
    AUTH = "AUTH"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    UPSTREAM = "UPSTREAM"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    # Bug di sisi kita (bukan layanan luar). Sengaja bukan UPSTREAM, yang di Bab 3 berarti layanan
    # luar gagal. Kosakata tambahan di luar Bab 3; lihat TASK-02-progress.md.
    INTERNAL_ERROR = "INTERNAL_ERROR"
    # SKIPPED
    ADAPTER_NOT_IMPLEMENTED = "ADAPTER_NOT_IMPLEMENTED"
    QUOTA_INTERNAL = "QUOTA_INTERNAL"  # dipakai pembatas kuota (Tahap 3)


# Flag per sumber. Digabung menjadi flag hasil akhir di Tahap 2.
FLAG_NO_VENDOR_OPINION = "NO_VENDOR_OPINION"
FLAG_SUMBER_SIMULASI = "SUMBER_SIMULASI"

SourceTimeType = Literal["last_report", "last_analysis"]


@dataclass(frozen=True)
class SourceResult:
    source: str
    status: SourceStatus
    reason: SourceReason | None = None
    # A (AbuseIPDB) atau V (VirusTotal), 0-100; null bila tidak dinilai.
    normalized_score: int | None = None
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    source_time: datetime | None = None
    source_time_type: SourceTimeType | None = None
    retrieved_at: datetime | None = None
    # Diisi lapisan cache (Tahap 3); adapter selalu mengembalikan nilai bawaan ini.
    expires_at: datetime | None = None
    from_cache: bool = False
    http_status: int | None = None
    duration_ms: int | None = None
    flags: tuple[str, ...] = ()
    # Detik dari header Retry-After pada 429, bila ada dan berupa angka.
    retry_after_seconds: int | None = None
    # Header X-RateLimit-* (AbuseIPDB). Dipakai pembatas kuota; tidak ditampilkan di API.
    rate_limit_reset: datetime | None = None
    rate_limit_remaining: int | None = None

    def __post_init__(self) -> None:
        needs_reason = self.status in REASON_REQUIRED_STATUSES
        if needs_reason and self.reason is None:
            raise ValueError(f"status {self.status} wajib menyertakan reason")
        if not needs_reason and self.reason is not None:
            raise ValueError(f"status {self.status} tidak boleh membawa reason")


class ReputationSource(Protocol):
    name: str

    def fetch(self, ip: str) -> SourceResult:
        """Ambil reputasi satu IPv4 publik yang SUDAH lolos validasi.

        Kegagalan dikembalikan sebagai `SourceResult` berstatus ERROR (tidak melempar),
        dan tidak pernah menjadi skor 0.
        """
        ...
