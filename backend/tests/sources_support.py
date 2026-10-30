"""Alat bantu test adapter sumber (TASK-02 Tahap 1). Tanpa jaringan: semua lewat `MockTransport`."""

import dataclasses
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from app.services.sources.abuseipdb import AbuseIpdbSource
from app.services.sources.base import (
    REASON_REQUIRED_STATUSES,
    SCORED_STATUSES,
    SourceReason,
    SourceResult,
    SourceStatus,
)
from app.services.sources.cache import CacheTtl
from app.services.sources.gateway import SourceGateway
from app.services.sources.quota import QuotaPolicy
from app.services.sources.virustotal import VirusTotalSource

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sources"
# Mudah dicari di URL, log, atau hasil bila bocor.
FAKE_KEY = "kunci-uji-palsu-xyz"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
TIMEOUT_SECONDS = 7.5

Responder = Callable[[httpx.Request], httpx.Response]


def fixture_text(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def fixture_json(name: str) -> Any:
    return json.loads(fixture_text(name))


def reply(
    status: int,
    *,
    fixture: str | None = None,
    body: object = None,
    raw: str | None = None,
    headers: dict[str, str] | None = None,
) -> Responder:
    """Responder: isi dari file fixture, objek JSON `body`, atau teks mentah `raw`."""
    if fixture is not None:
        content = fixture_text(fixture)
    elif raw is not None:
        content = raw
    else:
        content = json.dumps(body)
    return lambda request: httpx.Response(
        status, content=content.encode(), headers=headers, request=request
    )


def raises(exc_type: type[httpx.HTTPError]) -> Responder:
    def responder(request: httpx.Request) -> httpx.Response:
        # Pesan sengaja memuat kunci: adapter tidak boleh menyalin teks exception ke hasil.
        raise exc_type(f"gagal memakai {FAKE_KEY}", request=request)

    return responder


def client_for(responder: Responder) -> tuple[httpx.Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responder(request)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def assert_score_invariants(result: SourceResult) -> None:
    """Error/kosong TIDAK BOLEH menjadi skor: hanya OK_* yang membawa skor 0-100 (integer)."""
    if result.status in SCORED_STATUSES:
        assert isinstance(result.normalized_score, int)
        assert not isinstance(result.normalized_score, bool)
        assert 0 <= result.normalized_score <= 100
    else:
        assert result.normalized_score is None
    # reason wajib untuk ERROR/SKIPPED, null untuk status lain (Bab 3).
    assert (result.reason is not None) == (result.status in REASON_REQUIRED_STATUSES)
    assert result.from_cache is False
    assert result.expires_at is None


def leak_surfaces(result: SourceResult, adapter: object) -> list[str]:
    """Semua representasi teks yang tidak boleh memuat key."""
    return [repr(result), repr(dataclasses.asdict(result)), repr(adapter), str(adapter)]


NYATA_ABUSEIPDB = "abuseipdb_nyata_2026-10-29_118.25.6.39.json"
NYATA_VIRUSTOTAL = "virustotal_nyata_2026-10-29_118.25.6.39.json"


def live_adapters(abuse_responder: Responder, vt_responder: Responder):
    """Adapter live asli (bukan mock) di atas `MockTransport`, untuk uji ujung ke ujung."""
    return live_adapters_with_requests(abuse_responder, vt_responder)[0]


def live_adapters_with_requests(abuse_responder: Responder, vt_responder: Responder):
    """Seperti `live_adapters`, plus daftar request yang benar-benar dikirim tiap adapter."""
    abuse_client, abuse_seen = client_for(abuse_responder)
    vt_client, vt_seen = client_for(vt_responder)
    adapters = [
        AbuseIpdbSource(
            abuse_client,
            SecretStr(FAKE_KEY),
            max_age_days=30,
            timeout_seconds=TIMEOUT_SECONDS,
            clock=lambda: NOW,
        ),
        VirusTotalSource(
            vt_client,
            SecretStr(FAKE_KEY),
            timeout_seconds=TIMEOUT_SECONDS,
            clock=lambda: NOW,
        ),
    ]
    return adapters, abuse_seen, vt_seen


def post(client, login, ip: str, user: str = "analyst"):
    """`POST /checks` sebagai `user` (harus sudah dibuat dengan make_user)."""
    return client.post("/api/v1/checks", json={"ip": ip}, headers=login(user))


# --- gerbang cache + kuota (Tahap 3) ---------------------------------------------------------

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


class Clock:
    """Jam palsu yang bisa dimajukan; dipakai gerbang untuk cek kedaluwarsa dan jendela kuota."""

    def __init__(self, start: datetime = T0) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


def result_of(
    source: str,
    status: SourceStatus = SourceStatus.OK_SIGNAL,
    score: int | None = 50,
    *,
    reason: SourceReason | None = None,
    flags: tuple[str, ...] = (),
    evidence: dict | None = None,
    retrieved_at: datetime = T0,
    http_status: int | None = 200,
    retry_after: int | None = None,
    rate_limit_reset: datetime | None = None,
    rate_limit_remaining: int | None = None,
) -> SourceResult:
    if status not in SCORED_STATUSES:
        score = None
    if status in REASON_REQUIRED_STATUSES and reason is None:
        reason = SourceReason.UPSTREAM
    return SourceResult(
        source=source,
        status=status,
        reason=reason,
        normalized_score=score,
        evidence_summary=evidence if evidence is not None else {"k": 1},
        source_time=retrieved_at - timedelta(days=1),
        source_time_type="last_report",
        retrieved_at=retrieved_at,
        http_status=http_status,
        duration_ms=12,
        flags=flags,
        retry_after_seconds=retry_after,
        rate_limit_reset=rate_limit_reset,
        rate_limit_remaining=rate_limit_remaining,
    )


class FakeSource:
    """Sumber palsu: mencatat IP yang diminta; hasil lewat `respond(ip)` (bawaan: OK_SIGNAL)."""

    def __init__(
        self,
        name: str,
        respond: Callable[[str], SourceResult] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.name = name
        self.calls: list[str] = []
        self._clock = clock
        self._respond = respond or (lambda ip: self._default())

    def _default(self) -> SourceResult:
        at = self._clock() if self._clock else T0
        return result_of(self.name, retrieved_at=at)

    def fetch(self, ip: str) -> SourceResult:
        self.calls.append(ip)
        return self._respond(ip)


VT_POLICY = QuotaPolicy(per_minute=4, daily=500)
ABUSE_POLICY = QuotaPolicy(daily=1000, daily_reset_from_header=True)
DEFAULT_TTL = CacheTtl(
    ok_signal=timedelta(hours=6),
    ok_no_signal=timedelta(hours=24),
    no_record=timedelta(hours=1),
)


def make_gateway(
    inner,
    engine,
    *,
    clock: Callable[[], datetime] | None = None,
    mode: str = "live",
    policy: QuotaPolicy | None = None,
    params_key: str = "",
    ttl: CacheTtl = DEFAULT_TTL,
) -> SourceGateway:
    return SourceGateway(
        inner,
        engine=engine,
        mode=mode,
        params_key=params_key,
        policy=policy or (ABUSE_POLICY if inner.name == "abuseipdb" else VT_POLICY),
        ttl=ttl,
        **({"clock": clock} if clock is not None else {}),
    )
