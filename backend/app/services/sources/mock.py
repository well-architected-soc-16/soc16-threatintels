"""Adapter mock untuk `SOURCES_MODE=mock` (TASK-02 Tahap 1). Tidak menghubungi apa pun.

Hasilnya FIKTIF. Skenario dipilih lewat tabel IP demo (IP resolver publik terkenal, supaya hasil
"berbahaya" yang jelas palsu tidak mencoreng pihak kecil). Setiap hasil, termasuk yang ERROR,
diberi flag `SUMBER_SIMULASI` dan `"simulasi": true` di bukti. Payload sintetis dilewatkan ke
fungsi pemetaan adapter asli, sehingga mock dan live tidak bisa menyimpang satu sama lain.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from app.services.sources import abuseipdb, virustotal
from app.services.sources._common import error_result, require_public_ip, utc_now
from app.services.sources.base import (
    FLAG_SUMBER_SIMULASI,
    SourceReason,
    SourceResult,
)

# Pembuat hasil per sumber: menerima waktu pengambilan, mengembalikan hasil sebelum ditandai simulasi.
Scenario = Callable[[datetime], SourceResult]


def _abuse(
    score: int, *, reports: int, users: int, whitelisted: bool = False
) -> Scenario:
    body = {
        "data": {
            "abuseConfidenceScore": score,
            "totalReports": reports,
            "numDistinctUsers": users,
            "lastReportedAt": None,
            "isWhitelisted": whitelisted,
        }
    }
    return lambda now: abuseipdb.map_response_body(body, now)


def _vt(**stats: int) -> Scenario:
    body = {"data": {"attributes": {"last_analysis_stats": stats}}}
    return lambda now: virustotal.map_response_body(body, now)


def _fail(source: str, reason: SourceReason) -> Scenario:
    return lambda now: error_result(source, reason, retrieved_at=now)


def _vt_not_found(now: datetime) -> SourceResult:
    result = virustotal.map_not_found({"error": {"code": "NotFoundError"}}, now)
    assert result is not None
    return result


_ABUSE_TIMEOUT = _fail(abuseipdb.SOURCE_NAME, SourceReason.TIMEOUT)
_VT_TIMEOUT = _fail(virustotal.SOURCE_NAME, SourceReason.TIMEOUT)

# Hasil bawaan untuk IP di luar tabel: kedua sumber OK_NO_SIGNAL (0/0).
_DEFAULT: dict[str, Scenario] = {
    abuseipdb.SOURCE_NAME: _abuse(0, reports=0, users=0),
    virustotal.SOURCE_NAME: _vt(
        malicious=0, suspicious=0, harmless=60, undetected=30, timeout=0
    ),
}

# Pemetaan IP ke skenario adalah usulan dan boleh disesuaikan tim (lihat TASK-02, Tahap 1).
# Sumber yang tidak disebut pada suatu IP memakai hasil bawaan (OK_NO_SIGNAL, skor 0).
DEMO_SCENARIOS: dict[str, dict[str, Scenario]] = {
    "1.1.1.1": {
        abuseipdb.SOURCE_NAME: _abuse(90, reports=120, users=40),
        virustotal.SOURCE_NAME: _vt(
            malicious=10, suspicious=0, harmless=50, undetected=30, timeout=0
        ),
    },
    "1.0.0.1": {
        abuseipdb.SOURCE_NAME: _abuse(90, reports=120, users=40),
    },
    "8.8.8.8": {
        abuseipdb.SOURCE_NAME: _abuse(90, reports=120, users=40),
        virustotal.SOURCE_NAME: _VT_TIMEOUT,
    },
    "8.8.4.4": {
        abuseipdb.SOURCE_NAME: _ABUSE_TIMEOUT,
        virustotal.SOURCE_NAME: _vt_not_found,
    },
    "9.9.9.9": {
        abuseipdb.SOURCE_NAME: _abuse(90, reports=120, users=40, whitelisted=True),
        virustotal.SOURCE_NAME: _vt(
            malicious=10, suspicious=0, harmless=50, undetected=30, timeout=0
        ),
    },
    "149.112.112.112": {
        virustotal.SOURCE_NAME: _vt(
            malicious=0, suspicious=0, harmless=0, undetected=90, timeout=0
        ),
    },
    "208.67.222.222": {
        virustotal.SOURCE_NAME: _vt(
            malicious=0, suspicious=0, harmless=0, undetected=0, timeout=90
        ),
    },
}


def _mark_simulated(result: SourceResult) -> SourceResult:
    return replace(
        result,
        flags=(*result.flags, FLAG_SUMBER_SIMULASI),
        evidence_summary={**result.evidence_summary, "simulasi": True},
    )


class MockSource:
    def __init__(self, name: str, *, clock: Callable[[], datetime] = utc_now) -> None:
        if name not in _DEFAULT:
            raise ValueError(f"sumber tidak dikenal: {name}")
        self.name = name
        self._clock = clock

    def fetch(self, ip: str) -> SourceResult:
        ip = require_public_ip(ip)
        scenario = DEMO_SCENARIOS.get(ip, {}).get(self.name) or _DEFAULT[self.name]
        return _mark_simulated(scenario(self._clock()))
