"""Alat bantu test adapter sumber (TASK-02 Tahap 1). Tanpa jaringan: semua lewat `MockTransport`."""

import dataclasses
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.services.sources.base import (
    REASON_REQUIRED_STATUSES,
    SCORED_STATUSES,
    SourceResult,
)

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
