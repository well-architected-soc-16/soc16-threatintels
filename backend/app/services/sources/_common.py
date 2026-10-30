"""Bagian bersama adapter live AbuseIPDB dan VirusTotal.

Aturan yang ditegakkan di sini, supaya tidak tersebar di tiap adapter:
- status HTTP diklasifikasi lebih dulu; JSON hanya dibaca untuk 200 (dan 404 milik VirusTotal);
- redirect tidak diikuti (httpx meneruskan header kustom seperti `Key`/`x-apikey` ke tujuan baru);
- teks exception httpx tidak pernah disalin ke hasil (pesannya bisa memuat nilai header);
- IP divalidasi ulang sebelum request apa pun dibuat.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

import httpx

from app.services.ip_validation import validate_ip
from app.services.sources.base import (
    InputRejectedError,
    SourceReason,
    SourceResult,
    SourceStatus,
)

# Memetakan body 200 (atau 404) ke hasil; None dari map_not_found berarti "bukan 404 yang dikenal".
BodyMapper = Callable[[object, datetime], SourceResult]
NotFoundMapper = Callable[[object, datetime], SourceResult | None]

_RETRY_AFTER_SECONDS = re.compile(r"[0-9]{1,9}")
_HEADER_INTEGER = re.compile(r"[0-9]{1,12}")


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_public_ip(ip: str) -> str:
    """Kembalikan IP kanonik, atau lempar `InputRejectedError` tanpa membuat request.

    Pemanggil seharusnya sudah memvalidasi; ini pengaman terakhir karena VirusTotal
    menaruh IP di path URL.
    """
    result = validate_ip(ip)
    if not result.valid or result.ip is None:
        raise InputRejectedError(
            "adapter sumber hanya boleh dipanggil dengan IPv4 publik yang valid"
        )
    return result.ip


def is_int(value: object) -> bool:
    # bool adalah subclass int di Python; True bukan angka yang sah di sini.
    return isinstance(value, int) and not isinstance(value, bool)


def parse_iso_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def epoch_to_utc(value: object) -> datetime | None:
    if not is_int(value) or value < 0:
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def error_result(
    source: str,
    reason: SourceReason,
    *,
    retrieved_at: datetime,
    http_status: int | None = None,
    duration_ms: int | None = None,
    retry_after_seconds: int | None = None,
    rate_limit_reset: datetime | None = None,
    rate_limit_remaining: int | None = None,
) -> SourceResult:
    return SourceResult(
        source=source,
        status=SourceStatus.ERROR,
        reason=reason,
        retrieved_at=retrieved_at,
        http_status=http_status,
        duration_ms=duration_ms,
        retry_after_seconds=retry_after_seconds,
        rate_limit_reset=rate_limit_reset,
        rate_limit_remaining=rate_limit_remaining,
    )


@dataclass(frozen=True)
class HttpOutcome:
    # response None berarti request gagal sebelum ada respons; `error` menjelaskan alasannya.
    response: httpx.Response | None
    duration_ms: int
    error: SourceReason | None = None


def send_get(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
    params: dict[str, Any] | None = None,
) -> HttpOutcome:
    started = time.perf_counter()
    response: httpx.Response | None = None
    error: SourceReason | None = None
    try:
        # timeout dan follow_redirects ditetapkan per request: client bisa disuntikkan
        # dan tidak boleh dipercaya membawa nilai yang aman.
        response = client.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        error = SourceReason.TIMEOUT
    except httpx.HTTPError:
        error = SourceReason.UPSTREAM
    duration_ms = round((time.perf_counter() - started) * 1000)
    return HttpOutcome(response=response, duration_ms=duration_ms, error=error)


def _json_or_none(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError:  # JSONDecodeError dan UnicodeDecodeError
        return None


def _retry_after_seconds(response: httpx.Response) -> int | None:
    value = response.headers.get("Retry-After", "").strip()
    # Bentuk HTTP-date sengaja diabaikan; hanya detik yang dipakai limiter nanti.
    return int(value) if _RETRY_AFTER_SECONDS.fullmatch(value) else None


def _rate_limit_headers(response: httpx.Response) -> tuple[datetime | None, int | None]:
    """`X-RateLimit-Reset` (epoch) dan `X-RateLimit-Remaining` (AbuseIPDB); nilai yang tidak
    berupa bilangan bulat non-negatif diabaikan."""
    reset = response.headers.get("X-RateLimit-Reset", "").strip()
    remaining = response.headers.get("X-RateLimit-Remaining", "").strip()
    return (
        epoch_to_utc(int(reset)) if _HEADER_INTEGER.fullmatch(reset) else None,
        int(remaining) if _HEADER_INTEGER.fullmatch(remaining) else None,
    )


def _classify_status(status_code: int) -> SourceReason:
    if status_code in (401, 403):
        return SourceReason.AUTH
    if status_code == 429:
        return SourceReason.RATE_LIMIT
    return SourceReason.UPSTREAM  # 4xx lain, 3xx, 5xx, dan status tak terduga


def outcome_to_result(
    source: str,
    outcome: HttpOutcome,
    retrieved_at: datetime,
    *,
    map_ok: BodyMapper,
    map_not_found: NotFoundMapper | None = None,
) -> SourceResult:
    response = outcome.response
    if response is None:
        return error_result(
            source,
            outcome.error or SourceReason.UPSTREAM,
            retrieved_at=retrieved_at,
            duration_ms=outcome.duration_ms,
        )

    status_code = response.status_code
    if status_code == 200:
        mapped: SourceResult | None = map_ok(_json_or_none(response), retrieved_at)
    elif status_code == 404 and map_not_found is not None:
        mapped = map_not_found(_json_or_none(response), retrieved_at)
    else:
        mapped = None

    reset, remaining = _rate_limit_headers(response)
    if mapped is not None:
        return replace(
            mapped,
            http_status=status_code,
            duration_ms=outcome.duration_ms,
            rate_limit_reset=reset,
            rate_limit_remaining=remaining,
        )
    return error_result(
        source,
        _classify_status(status_code),
        retrieved_at=retrieved_at,
        http_status=status_code,
        duration_ms=outcome.duration_ms,
        retry_after_seconds=(
            _retry_after_seconds(response) if status_code == 429 else None
        ),
        rate_limit_reset=reset,
        rate_limit_remaining=remaining,
    )
