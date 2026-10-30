"""Pembatas kuota bersama berbasis tabel `source_calls` (TASK-02 Tahap 3; Bab 5).

Kuota dipakai bersama semua user (satu API key per sumber), jadi hitungannya global, bukan
per user. Alur `reserve`: dalam SATU transaksi, ambil `pg_advisory_xact_lock` per sumber, hitung
panggilan `mode = 'live'`, cek cooldown, lalu sisipkan baris reservasi sebelum request dikirim.
Pemanggil meng-commit transaksi itu (melepas lock) SEBELUM request HTTP, lalu memanggil `finalize`.

Semua baris dihitung, termasuk reservasi yang tak pernah selesai (`result_status` NULL): lebih
baik menolak terlalu dini daripada menembus kuota. Panggilan `mock` dicatat tetapi tidak dihitung.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.models import SourceCall
from app.services.sources.base import SourceResult

# Cooldown bila 429 datang tanpa header Retry-After.
DEFAULT_COOLDOWN_SECONDS = 60
_MINUTE = timedelta(seconds=60)
_DAY = timedelta(days=1)


@dataclass(frozen=True)
class QuotaPolicy:
    per_minute: int | None = None
    daily: int | None = None
    # AbuseIPDB: reset harian mengikuti header X-RateLimit-Reset dari respons terakhir.
    # Tanpa header (atau bernilai False): 00:00 UTC.
    daily_reset_from_header: bool = False


def daily_window_start(now: datetime, anchor: datetime | None = None) -> datetime:
    """Awal jendela harian yang sedang berjalan.

    `anchor` adalah salah satu waktu reset (boleh di masa lalu atau depan); reset berulang tiap
    24 jam dari titik itu. Tanpa anchor dipakai 00:00 UTC hari ini.
    """
    if anchor is None:
        anchor = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return anchor + _DAY * ((now - anchor) // _DAY)


def _lock(session: Session, source: str) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"source_quota:{source}"},
    )


def _live_calls(source: str):
    return (
        select(func.count())
        .select_from(SourceCall)
        .where(SourceCall.source == source, SourceCall.mode == "live")
    )


def _in_cooldown(session: Session, source: str, now: datetime) -> bool:
    last = session.execute(
        select(SourceCall.called_at, SourceCall.retry_after_seconds)
        .where(
            SourceCall.source == source,
            SourceCall.mode == "live",
            SourceCall.http_status == 429,
        )
        .order_by(SourceCall.called_at.desc(), SourceCall.id.desc())
        .limit(1)
    ).first()
    if last is None:
        return False
    wait = last.retry_after_seconds
    if wait is None:
        wait = DEFAULT_COOLDOWN_SECONDS
    return now < last.called_at + timedelta(seconds=wait)


def _daily_anchor(
    session: Session, source: str, policy: QuotaPolicy
) -> datetime | None:
    if not policy.daily_reset_from_header:
        return None
    return session.scalar(
        select(SourceCall.rate_limit_reset)
        .where(
            SourceCall.source == source,
            SourceCall.mode == "live",
            SourceCall.rate_limit_reset.is_not(None),
        )
        .order_by(SourceCall.called_at.desc(), SourceCall.id.desc())
        .limit(1)
    )


def reserve(
    session: Session, *, source: str, mode: str, policy: QuotaPolicy, now: datetime
) -> int | None:
    """Buat baris reservasi dan kembalikan id-nya, atau None bila kuota/cooldown menolak.

    Harus dijalankan di dalam transaksi (READ COMMITTED) yang di-commit pemanggil. Mode `mock`
    hanya mencatat: tidak ada lock, tidak ada pembatasan.
    """
    if mode == "live":
        _lock(session, source)
        if _in_cooldown(session, source, now):
            return None
        if policy.per_minute is not None:
            recent = session.scalar(
                _live_calls(source).where(SourceCall.called_at > now - _MINUTE)
            )
            if (recent or 0) >= policy.per_minute:
                return None
        if policy.daily is not None:
            start = daily_window_start(now, _daily_anchor(session, source, policy))
            today = session.scalar(
                _live_calls(source).where(SourceCall.called_at >= start)
            )
            if (today or 0) >= policy.daily:
                return None

    call = SourceCall(source=source, mode=mode, called_at=now)
    session.add(call)
    session.flush()
    return call.id


def finalize(session: Session, call_id: int, result: SourceResult) -> None:
    """Lengkapi baris reservasi dengan hasil. Tanpa key, header request, maupun body."""
    session.execute(
        update(SourceCall)
        .where(SourceCall.id == call_id)
        .values(
            http_status=result.http_status,
            result_status=result.status.value,
            reason=result.reason.value if result.reason is not None else None,
            duration_ms=result.duration_ms,
            retry_after_seconds=result.retry_after_seconds,
            rate_limit_reset=result.rate_limit_reset,
            rate_limit_remaining=result.rate_limit_remaining,
        )
    )
