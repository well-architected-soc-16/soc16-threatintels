"""Cache hasil per sumber (TASK-02 Tahap 3; Bab 5).

Hanya `OK_SIGNAL`, `OK_NO_SIGNAL`, dan `NO_RECORD` yang disimpan. `ERROR`, `INSUFFICIENT_DATA`,
dan `SKIPPED` tidak pernah di-cache. Baris kedaluwarsa tidak pernah dipakai; satu baris per
(`source`, `ip`, `params_key`, `mode`) dan mode live tidak pernah membaca baris mock.

Fungsi di sini hanya boleh dipanggil dari `SourceGateway.fetch`, yaitu SETELAH `validate_ip` lolos.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import SourceCache
from app.services.sources.base import SourceResult, SourceStatus


@dataclass(frozen=True)
class CacheTtl:
    """TTL per status; nilai percobaan, belum disepakati tim (lihat config)."""

    ok_signal: timedelta
    ok_no_signal: timedelta
    no_record: timedelta

    def for_status(self, status: SourceStatus) -> timedelta | None:
        """None = status ini tidak boleh di-cache."""
        return {
            SourceStatus.OK_SIGNAL: self.ok_signal,
            SourceStatus.OK_NO_SIGNAL: self.ok_no_signal,
            SourceStatus.NO_RECORD: self.no_record,
        }.get(status)


def lookup(
    session: Session,
    *,
    source: str,
    ip: str,
    params_key: str,
    mode: str,
    now: datetime,
) -> SourceResult | None:
    row = session.scalar(
        select(SourceCache).where(
            SourceCache.source == source,
            SourceCache.ip == ip,
            SourceCache.params_key == params_key,
            SourceCache.mode == mode,
            SourceCache.expires_at > now,
        )
    )
    if row is None:
        return None
    return SourceResult(
        source=row.source,
        status=SourceStatus(row.status),
        normalized_score=row.normalized_score,
        evidence_summary=row.evidence_summary,
        source_time=row.source_time,
        source_time_type=row.source_time_type,  # type: ignore[arg-type]
        # Waktu pengambilan ASLI, tidak diubah; hasil dari cache bukan pengambilan baru.
        retrieved_at=row.retrieved_at,
        expires_at=row.expires_at,
        from_cache=True,
        # Tidak ada request pada pembacaan ini, jadi tidak ada status HTTP maupun durasi.
        flags=tuple(row.flags),
    )


def store(
    session: Session,
    result: SourceResult,
    *,
    ip: str,
    params_key: str,
    mode: str,
    expires_at: datetime,
    fallback_retrieved_at: datetime,
) -> None:
    """Upsert. Pemanggil harus sudah memastikan `result.status` boleh di-cache."""
    values = {
        "source": result.source,
        "ip": ip,
        "params_key": params_key,
        "mode": mode,
        "status": result.status.value,
        "normalized_score": result.normalized_score,
        "evidence_summary": result.evidence_summary,
        "flags": list(result.flags),
        "source_time": result.source_time,
        "source_time_type": result.source_time_type,
        "retrieved_at": result.retrieved_at or fallback_retrieved_at,
        "expires_at": expires_at,
    }
    stmt = insert(SourceCache).values(**values)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["source", "ip", "params_key", "mode"],
            set_={
                k: stmt.excluded[k]
                for k in values
                if k not in {"source", "ip", "params_key", "mode"}
            },
        )
    )
