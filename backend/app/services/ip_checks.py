"""Pengumpulan hasil sumber reputasi dan penilaian untuk satu IP yang SUDAH tervalidasi.

Pemanggil wajib memvalidasi IP lebih dulu (`validate_ip`); input yang ditolak tidak boleh sampai
ke adapter. Rumus skor, label, dan flag ada di `app.services.scoring`.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.services import scoring
from app.services.sources._common import error_result, utc_now
from app.services.sources.base import (
    SCORED_STATUSES,
    ReputationSource,
    SourceReason,
    SourceResult,
)

logger = logging.getLogger(__name__)

SCORING_VERSION = scoring.SCORING_VERSION


@dataclass(frozen=True)
class Assessment:
    assessment_status: str
    coverage: str
    # None = tidak dapat dinilai. Error/data kosong tidak pernah menjadi 0.
    risk_score: float | None
    flags: list[str]


def collect_sources(ip: str, sources: Sequence[ReputationSource]) -> list[SourceResult]:
    """Seam ke adapter. Berurutan (Keputusan 5); kegagalan layanan luar sudah menjadi hasil ERROR
    di adapter.

    Isolasi per sumber (known gap 11): exception tak terduga pada satu sumber, yaitu bug di sisi
    kita, menjadi `ERROR` + `INTERNAL_ERROR` untuk sumber itu saja dan sumber lain tetap tampil.
    Log level ERROR hanya memuat nama sumber dan nama kelas exception, tanpa pesan dan tanpa
    traceback (pesan bisa memuat data sensitif). Hasil itu tidak masuk cache (ia dibuat di luar
    gerbang) dan reservasi kuota yang sudah dibuat tetap dihitung.

    `ValueError` sengaja tetap dilempar keras: ia berarti input yang ditolak lolos ke adapter
    (`require_public_ip`), bukan kegagalan satu sumber.
    """
    results: list[SourceResult] = []
    for source in sources:
        try:
            results.append(source.fetch(ip))
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "sumber %s gagal tak terduga: %s", source.name, type(exc).__name__
            )
            results.append(
                error_result(
                    source.name, SourceReason.INTERNAL_ERROR, retrieved_at=utc_now()
                )
            )
    return results


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
