"""Adapter VirusTotal `GET /api/v3/ip_addresses/{ip}` (TASK-02 Tahap 1).

Dokumentasi: https://docs.virustotal.com/reference/ip-object dan .../reference/errors .
Key hanya dikirim lewat header `x-apikey`. Dari objek IP hanya `last_analysis_stats` dan
`last_analysis_date` yang dipakai; `whois`, `rdap`, dan `last_analysis_results` (besar dan memuat
data kontak) tidak pernah disalin ke hasil.
"""

from collections.abc import Callable
from datetime import datetime

import httpx
from pydantic import SecretStr

from app.services.sources._common import (
    epoch_to_utc,
    error_result,
    is_int,
    outcome_to_result,
    require_public_ip,
    send_get,
    utc_now,
)
from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    SourceReason,
    SourceResult,
    SourceStatus,
)

SOURCE_NAME = "virustotal"
IP_URL = "https://www.virustotal.com/api/v3/ip_addresses/{ip}"

# Kunci statistik yang dipakai rumus; kunci lain di `last_analysis_stats` diabaikan.
_STAT_KEYS = ("malicious", "suspicious", "harmless", "undetected", "timeout")
MALICIOUS_WEIGHT = 8
SUSPICIOUS_WEIGHT = 4


def _invalid(retrieved_at: datetime) -> SourceResult:
    return error_result(
        SOURCE_NAME, SourceReason.INVALID_RESPONSE, retrieved_at=retrieved_at
    )


def map_response_body(body: object, retrieved_at: datetime) -> SourceResult:
    """Petakan body respons 200 ke hasil. Dipakai juga oleh adapter mock.

    - `last_analysis_stats` hilang atau bukan objek -> `ERROR` + `INVALID_RESPONSE`.
    - Nilai statistik yang ada harus integer >= 0 (bukan bool); kunci yang tidak ada dihitung 0.
    - Statistik kosong, atau tidak ada mesin yang menilai (semua `timeout`) -> `INSUFFICIENT_DATA`.
    """
    data = body.get("data") if isinstance(body, dict) else None
    attributes = data.get("attributes") if isinstance(data, dict) else None
    stats = (
        attributes.get("last_analysis_stats") if isinstance(attributes, dict) else None
    )
    if not isinstance(attributes, dict) or not isinstance(stats, dict):
        return _invalid(retrieved_at)

    evidence: dict[str, int] = {}
    for key in _STAT_KEYS:
        if key not in stats:
            continue
        value = stats[key]
        if not is_int(value) or value < 0:
            return _invalid(retrieved_at)
        evidence[key] = value

    malicious = evidence.get("malicious", 0)
    suspicious = evidence.get("suspicious", 0)
    harmless = evidence.get("harmless", 0)
    undetected = evidence.get("undetected", 0)

    flags: tuple[str, ...] = ()
    score: int | None
    if malicious + suspicious + harmless + undetected == 0:
        status, score = SourceStatus.INSUFFICIENT_DATA, None
    elif malicious > 0 or suspicious > 0:
        status = SourceStatus.OK_SIGNAL
        score = min(100, MALICIOUS_WEIGHT * malicious + SUSPICIOUS_WEIGHT * suspicious)
    else:
        # Tidak ada mesin yang menandai. Bila tak satu pun menyatakan aman (hanya `undetected`),
        # skor 0 tetap sah tetapi bukan pendapat vendor.
        status, score = SourceStatus.OK_NO_SIGNAL, 0
        if harmless == 0:
            flags = (FLAG_NO_VENDOR_OPINION,)

    return SourceResult(
        source=SOURCE_NAME,
        status=status,
        normalized_score=score,
        evidence_summary=evidence,
        source_time=epoch_to_utc(attributes.get("last_analysis_date")),
        source_time_type="last_analysis",
        retrieved_at=retrieved_at,
        flags=flags,
    )


def map_not_found(body: object, retrieved_at: datetime) -> SourceResult | None:
    """404 berkode `NotFoundError` = objek memang tidak ada (`NO_RECORD`); 404 lain -> None."""
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("code") == "NotFoundError":
        return SourceResult(
            source=SOURCE_NAME, status=SourceStatus.NO_RECORD, retrieved_at=retrieved_at
        )
    return None


class VirusTotalSource:
    name = SOURCE_NAME

    def __init__(
        self,
        client: httpx.Client,
        api_key: SecretStr,
        *,
        timeout_seconds: float,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def fetch(self, ip: str) -> SourceResult:
        ip = require_public_ip(ip)
        outcome = send_get(
            self._client,
            IP_URL.format(ip=ip),
            headers={
                "x-apikey": self._api_key.get_secret_value(),
                "Accept": "application/json",
            },
            timeout=self._timeout_seconds,
        )
        return outcome_to_result(
            self.name,
            outcome,
            self._clock(),
            map_ok=map_response_body,
            map_not_found=map_not_found,
        )
