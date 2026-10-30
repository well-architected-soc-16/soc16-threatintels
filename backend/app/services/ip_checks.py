"""Pengumpulan hasil sumber reputasi dan penilaian untuk satu IP yang SUDAH tervalidasi.

Pemanggil wajib memvalidasi IP lebih dulu (`validate_ip`); input yang ditolak tidak boleh sampai
ke adapter. Rumus skor, label, dan flag ada di `app.services.scoring`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.services import scoring
from app.services.sources.base import SCORED_STATUSES, ReputationSource, SourceResult

SCORING_VERSION = scoring.SCORING_VERSION


@dataclass(frozen=True)
class Assessment:
    assessment_status: str
    coverage: str
    # None = tidak dapat dinilai. Error/data kosong tidak pernah menjadi 0.
    risk_score: float | None
    flags: list[str]


def collect_sources(ip: str, sources: Sequence[ReputationSource]) -> list[SourceResult]:
    """Seam ke adapter. Berurutan (Keputusan 5); kegagalan sumber sudah menjadi hasil ERROR di adapter.

    Exception lain (mis. `ValueError` karena IP tidak valid) sengaja tidak ditangkap: itu berarti
    input yang ditolak lolos ke adapter, dan harus gagal keras, bukan dicatat sebagai `UPSTREAM`.
    """
    return [source.fetch(ip) for source in sources]


def assess(results: Sequence[SourceResult]) -> Assessment:
    # Hanya OK_SIGNAL dan OK_NO_SIGNAL yang menambah cakupan (Bab 3).
    assessed = sum(1 for r in results if r.status in SCORED_STATUSES)
    total = len(results)
    if assessed == 0:
        status = "TIDAK_TERSEDIA"
    elif assessed == total:
        status = "COMPLETE"
    else:
        status = "DATA_TERBATAS"
    return Assessment(
        assessment_status=status,
        coverage=f"{assessed}/{total}",
        risk_score=scoring.combined_score(results),
        flags=scoring.derive_flags(results),
    )


def _iso_utc(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value is not None else None


def to_stored(result: SourceResult) -> dict[str, Any]:
    """Bentuk JSON untuk kolom `ip_checks.sources` (JSONB). Waktu disimpan UTC; WIB hanya di respons."""
    return {
        "source": result.source,
        "status": result.status.value,
        "reason": result.reason.value if result.reason is not None else None,
        "normalized_score": result.normalized_score,
        "evidence_summary": result.evidence_summary,
        "source_time": _iso_utc(result.source_time),
        "source_time_type": result.source_time_type,
        "retrieved_at": _iso_utc(result.retrieved_at),
        "expires_at": _iso_utc(result.expires_at),
        "from_cache": result.from_cache,
        "http_status": result.http_status,
        "duration_ms": result.duration_ms,
        "flags": list(result.flags),
        "retry_after_seconds": result.retry_after_seconds,
    }
