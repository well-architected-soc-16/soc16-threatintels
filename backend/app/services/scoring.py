"""Skor gabungan, label indikasi, dan flag (TASK-02 Tahap 2; Bab 4 dokumen riset tim).

Fungsi murni tanpa I/O. Bobot, koefisien, dan ambang label berstatus PERCOBAAN (`scoring_version`
`v1-percobaan`): jangan diubah tanpa keputusan tim.
"""

from collections.abc import Sequence
from typing import Literal

from app.services.sources import abuseipdb, virustotal
from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    FLAG_SUMBER_SIMULASI,
    SCORED_STATUSES,
    SourceResult,
)

SCORING_VERSION = "v1-percobaan"

WEIGHT_ABUSEIPDB = 30
WEIGHT_VIRUSTOTAL = 25
# Selisih |A-V| sebesar ini atau lebih menandai dua sumber yang tidak sepakat.
DIVERGENCE_THRESHOLD = 50

FLAG_HASIL_BERBEDA = "HASIL_BERBEDA"
FLAG_WHITELISTED = "WHITELISTED"
# Urutan tetap, tanpa duplikat: hasil POST sama persis dengan GET.
FLAG_ORDER = (
    FLAG_HASIL_BERBEDA,
    FLAG_NO_VENDOR_OPINION,
    FLAG_WHITELISTED,
    FLAG_SUMBER_SIMULASI,
)

Indication = Literal["RENDAH", "PERLU_PEMERIKSAAN", "TINGGI", "SANGAT_TINGGI"]


def _scored(results: Sequence[SourceResult], name: str) -> int | None:
    """Skor ternormalisasi sumber `name`, atau None bila sumbernya tidak ada / tidak bisa dinilai."""
    for result in results:
        if (
            result.source == name
            and result.status in SCORED_STATUSES
            and result.normalized_score is not None
        ):
            return result.normalized_score
    return None


def combined_score(results: Sequence[SourceResult]) -> float | None:
    """`(30*A + 25*V) / 55`, hanya jika KEDUA sumber bisa dinilai; selain itu None (bukan 0)."""
    a = _scored(results, abuseipdb.SOURCE_NAME)
    v = _scored(results, virustotal.SOURCE_NAME)
    if a is None or v is None:
        return None
    return (WEIGHT_ABUSEIPDB * a + WEIGHT_VIRUSTOTAL * v) / (
        WEIGHT_ABUSEIPDB + WEIGHT_VIRUSTOTAL
    )


def indication(score: float | None) -> Indication | None:
    """Label dari nilai SEBELUM pembulatan (74,96 tampil `75.0` tetapi tetap `TINGGI`)."""
    if score is None:
        return None
    if score < 25:
        return "RENDAH"
    if score < 50:
        return "PERLU_PEMERIKSAAN"
    if score < 75:
        return "TINGGI"
    return "SANGAT_TINGGI"


def derive_flags(results: Sequence[SourceResult]) -> list[str]:
    """Flag tingkat cek. Dikumpulkan dari SEMUA hasil, bukan hanya yang bisa dinilai:
    cek simulasi yang `TIDAK_TERSEDIA` tetap harus ber-flag `SUMBER_SIMULASI`."""
    flags: set[str] = set()
    for result in results:
        flags.update(
            f
            for f in result.flags
            if f in (FLAG_NO_VENDOR_OPINION, FLAG_SUMBER_SIMULASI)
        )
        # null (atau hilang) berarti tidak ada flag; tidak memangkas skor.
        if (
            result.source == abuseipdb.SOURCE_NAME
            and result.evidence_summary.get("isWhitelisted") is True
        ):
            flags.add(FLAG_WHITELISTED)

    a = _scored(results, abuseipdb.SOURCE_NAME)
    v = _scored(results, virustotal.SOURCE_NAME)
    if a is not None and v is not None and abs(a - v) >= DIVERGENCE_THRESHOLD:
        flags.add(FLAG_HASIL_BERBEDA)

    return [f for f in FLAG_ORDER if f in flags]
