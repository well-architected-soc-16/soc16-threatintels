"""Constraint database untuk `source_cache` dan `source_calls` (TASK-02 Tahap 3)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SourceCache, SourceCall

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def cache_row(**override) -> SourceCache:
    values = {
        "source": "virustotal",
        "ip": "8.8.8.8",
        "params_key": "",
        "mode": "live",
        "status": "OK_SIGNAL",
        "normalized_score": 10,
        "evidence_summary": {},
        "flags": [],
        "retrieved_at": NOW,
        "expires_at": NOW,
        **override,
    }
    return SourceCache(**values)


def insert_fails(db: Session, row) -> bool:
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return True
    return False


def test_cache_unik_per_source_ip_params_dan_mode(db):
    db.add(cache_row())
    db.commit()

    assert insert_fails(db, cache_row()) is True
    # Beda salah satu kunci: boleh.
    for override in (
        {"mode": "mock"},
        {"params_key": "x"},
        {"ip": "1.1.1.1"},
        {"source": "abuseipdb"},
    ):
        assert insert_fails(db, cache_row(**override)) is False


@pytest.mark.parametrize("status", ["ERROR", "INSUFFICIENT_DATA", "SKIPPED", "lainnya"])
def test_cache_menolak_status_yang_tidak_boleh_disimpan(db, status):
    assert insert_fails(db, cache_row(status=status)) is True


@pytest.mark.parametrize("status", ["OK_SIGNAL", "OK_NO_SIGNAL", "NO_RECORD"])
def test_cache_menerima_status_yang_boleh_disimpan(db, status):
    assert insert_fails(db, cache_row(status=status)) is False


def test_mode_hanya_mock_atau_live(db):
    assert insert_fails(db, cache_row(mode="staging")) is True
    assert (
        insert_fails(db, SourceCall(source="virustotal", mode="staging", called_at=NOW))
        is True
    )
    assert (
        insert_fails(db, SourceCall(source="virustotal", mode="live", called_at=NOW))
        is False
    )
    assert (
        insert_fails(db, SourceCall(source="virustotal", mode="mock", called_at=NOW))
        is False
    )


def test_baris_reservasi_boleh_belum_punya_hasil(db):
    call = SourceCall(source="virustotal", mode="live", called_at=NOW)
    db.add(call)
    db.commit()

    assert (call.result_status, call.http_status, call.duration_ms) == (
        None,
        None,
        None,
    )
