"""Pengumpulan hasil sumber reputasi untuk satu IP yang SUDAH tervalidasi.

Adapter AbuseIPDB dan VirusTotal belum diimplementasikan (task berikutnya).
Sampai saat itu setiap sumber dilaporkan apa adanya sebagai SKIPPED, bukan skor 0.
"""

from typing import Any

SCORING_VERSION = "v1-percobaan"
SOURCE_NAMES = ("abuseipdb", "virustotal")

# Status sumber yang dihitung sebagai "bisa dinilai" untuk coverage.
_ASSESSABLE = frozenset({"OK_SIGNAL", "OK_NO_SIGNAL"})


def collect_sources(ip: str) -> list[dict[str, Any]]:
    """Seam untuk adapter eksternal. Hanya boleh dipanggil untuk IP yang lolos validasi."""
    return [
        {"source": name, "status": "SKIPPED", "reason": "ADAPTER_NOT_IMPLEMENTED"}
        for name in SOURCE_NAMES
    ]


def assess(sources: list[dict[str, Any]]) -> tuple[str, str, float | None]:
    """Mengembalikan (assessment_status, coverage, risk_score)."""
    assessed = sum(1 for s in sources if s["status"] in _ASSESSABLE)
    total = len(sources)
    coverage = f"{assessed}/{total}"
    status = {total: "COMPLETE", 0: "TIDAK_TERSEDIA"}.get(assessed, "DATA_TERBATAS")
    # Skor gabungan belum ada (di luar lingkup task ini); null = tidak dihitung.
    return status, coverage, None
