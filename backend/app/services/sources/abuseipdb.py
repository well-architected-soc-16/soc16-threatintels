"""Adapter AbuseIPDB `GET /api/v2/check` (TASK-02 Tahap 1).

Dokumentasi: https://docs.abuseipdb.com/ . Key hanya dikirim lewat header `Key`, tidak pernah di
query string. Parameter `verbose` sengaja tidak dikirim: ia mengembalikan laporan individual
dengan komentar teks bebas yang bisa memuat data pribadi.
"""

from collections.abc import Callable
from datetime import datetime

import httpx
from pydantic import SecretStr

from app.services.sources._common import (
    error_result,
    is_int,
    outcome_to_result,
    parse_iso_utc,
    require_public_ip,
    send_get,
    utc_now,
)
from app.services.sources.base import SourceReason, SourceResult, SourceStatus

SOURCE_NAME = "abuseipdb"
CHECK_URL = "https://api.abuseipdb.com/api/v2/check"


def map_response_body(body: object, retrieved_at: datetime) -> SourceResult:
    """Petakan body respons 200 ke hasil. Dipakai juga oleh adapter mock.

    Hanya `abuseConfidenceScore` yang wajib (integer 0-100, bukan bool/float). Field bukti lain
    yang hilang atau salah tipe menjadi null dan tidak menggagalkan skor: `lastReportedAt` dan
    `isWhitelisted` memang bisa null di API. Nol laporan (`totalReports=0`) BUKAN `NO_RECORD`.
    """
    data = body.get("data") if isinstance(body, dict) else None
    score = data.get("abuseConfidenceScore") if isinstance(data, dict) else None
    if not isinstance(data, dict) or not is_int(score) or not 0 <= score <= 100:
        return error_result(
            SOURCE_NAME, SourceReason.INVALID_RESPONSE, retrieved_at=retrieved_at
        )

    last_reported = data.get("lastReportedAt")
    source_time = parse_iso_utc(last_reported)
    total_reports = data.get("totalReports")
    distinct_users = data.get("numDistinctUsers")
    whitelisted = data.get("isWhitelisted")
    evidence = {
        "abuseConfidenceScore": score,
        "totalReports": total_reports if is_int(total_reports) else None,
        "numDistinctUsers": distinct_users if is_int(distinct_users) else None,
        "lastReportedAt": last_reported if source_time is not None else None,
        "isWhitelisted": whitelisted if isinstance(whitelisted, bool) else None,
    }
    return SourceResult(
        source=SOURCE_NAME,
        status=SourceStatus.OK_SIGNAL if score > 0 else SourceStatus.OK_NO_SIGNAL,
        normalized_score=score,
        evidence_summary=evidence,
        source_time=source_time,
        source_time_type="last_report",
        retrieved_at=retrieved_at,
    )


class AbuseIpdbSource:
    name = SOURCE_NAME

    def __init__(
        self,
        client: httpx.Client,
        api_key: SecretStr,
        *,
        max_age_days: int,
        timeout_seconds: float,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._max_age_days = max_age_days
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def fetch(self, ip: str) -> SourceResult:
        ip = require_public_ip(ip)
        outcome = send_get(
            self._client,
            CHECK_URL,
            params={"ipAddress": ip, "maxAgeInDays": self._max_age_days},
            headers={
                "Key": self._api_key.get_secret_value(),
                "Accept": "application/json",
            },
            timeout=self._timeout_seconds,
        )
        return outcome_to_result(
            self.name, outcome, self._clock(), map_ok=map_response_body
        )
