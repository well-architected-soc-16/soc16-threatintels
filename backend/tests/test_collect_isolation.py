"""Isolasi per sumber di `collect_sources` (TASK-02 Tahap 3; known gap 11).

Exception tak terduga pada satu sumber menjadi `ERROR` + `INTERNAL_ERROR` untuk sumber itu saja;
sumber lain tetap tampil. Log level ERROR hanya memuat nama sumber dan nama kelas exception
(tanpa pesan, tanpa traceback). `ValueError` tetap dilempar keras. Hasil itu tidak di-cache dan
reservasi kuotanya tetap dihitung.
"""

import json
import logging

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import app
from app.models import AuditLog, Role, SourceCache, SourceCall
from app.services import ip_checks
from app.services.sources.base import SourceReason, SourceStatus
from app.services.sources.factory import get_sources
from app.services.sources.mock import MockSource
from app.services.sources.quota import QuotaPolicy
from tests.sources_support import (
    Clock,
    FakeSource,
    assert_score_invariants,
    make_gateway,
    post,
)

SECRET = "berisi-rahasia"
A, V = "abuseipdb", "virustotal"


def raising(name: str, exc: Exception) -> FakeSource:
    def boom(ip):
        raise exc

    return FakeSource(name, boom)


def error_logs(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


# --- unit: collect_sources -----------------------------------------------------------------------------


def test_runtime_error_satu_sumber_sumber_lain_tetap_tampil():
    sources = [raising(A, RuntimeError(SECRET)), MockSource(V)]

    results = ip_checks.collect_sources("1.1.1.1", sources)

    broken, healthy = results
    assert (broken.source, broken.status, broken.reason) == (
        A,
        SourceStatus.ERROR,
        SourceReason.INTERNAL_ERROR,
    )
    assert broken.normalized_score is None  # error tidak pernah menjadi skor 0
    assert healthy.source == V and healthy.status is not SourceStatus.ERROR
    assessment = ip_checks.assess(results)
    assert (assessment.assessment_status, assessment.coverage) == (
        "DATA_TERBATAS",
        "1/2",
    )
    assert assessment.risk_score is None
    for r in results:
        assert_score_invariants(r)


def test_log_memuat_nama_sumber_dan_kelas_tetapi_tidak_pesan_atau_traceback(caplog):
    caplog.set_level(logging.DEBUG)

    ip_checks.collect_sources(
        "8.8.8.8", [raising(A, RuntimeError(SECRET)), MockSource(V)]
    )

    (record,) = error_logs(caplog)
    assert record.levelno == logging.ERROR
    assert A in record.getMessage() and "RuntimeError" in record.getMessage()
    assert record.exc_info is None
    assert SECRET not in caplog.text
    assert "Traceback" not in caplog.text


def test_hasil_internal_error_tidak_membawa_pesan_exception():
    (result,) = ip_checks.collect_sources("8.8.8.8", [raising(A, RuntimeError(SECRET))])

    assert SECRET not in repr(result)
    assert SECRET not in json.dumps(ip_checks.to_stored(result))


def test_semua_sumber_crash_tidak_tersedia_bukan_skor_nol():
    results = ip_checks.collect_sources(
        "8.8.8.8", [raising(A, KeyError(SECRET)), raising(V, RuntimeError(SECRET))]
    )
    assessment = ip_checks.assess(results)

    assert [r.reason for r in results] == [SourceReason.INTERNAL_ERROR] * 2
    assert (assessment.assessment_status, assessment.coverage) == (
        "TIDAK_TERSEDIA",
        "0/2",
    )
    assert assessment.risk_score is None


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("x"),
        json.JSONDecodeError("m", "d", 0),
        UnicodeDecodeError("utf-8", b"", 0, 1, "m"),
    ],
)
def test_value_error_dan_turunannya_tetap_dilempar_keras(exc):
    with pytest.raises(ValueError):
        ip_checks.collect_sources("8.8.8.8", [raising(A, exc), MockSource(V)])


def test_ip_ditolak_yang_lolos_ke_adapter_gagal_keras_bukan_internal_error():
    # Jalur nyata: require_public_ip di dalam adapter melempar ValueError untuk IP privat.
    with pytest.raises(ValueError):
        ip_checks.collect_sources("10.0.0.1", [MockSource(A), MockSource(V)])


def test_urutan_hasil_tetap_walau_sumber_pertama_crash():
    results = ip_checks.collect_sources(
        "8.8.8.8", [raising(A, RuntimeError(SECRET)), MockSource(V)]
    )

    assert [r.source for r in results] == [A, V]


# --- melalui gerbang: tidak di-cache, reservasi tetap dihitung ---------------------------------------------


def test_internal_error_tidak_masuk_cache_dan_reservasi_tetap_dihitung(engine, db):
    clock = Clock()
    gateway = make_gateway(
        raising(V, RuntimeError(SECRET)),
        engine,
        clock=clock,
        policy=QuotaPolicy(per_minute=2),
    )

    first = ip_checks.collect_sources("8.8.8.8", [gateway])[0]
    second = ip_checks.collect_sources("1.1.1.1", [gateway])[0]
    third = ip_checks.collect_sources("9.9.9.9", [gateway])[0]

    assert first.reason is second.reason is SourceReason.INTERNAL_ERROR
    # Dua reservasi yang tak pernah selesai sudah memakai batas 2/menit.
    assert (third.status, third.reason) == (
        SourceStatus.SKIPPED,
        SourceReason.QUOTA_INTERNAL,
    )
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SourceCache)) == 0
        rows = list(session.scalars(select(SourceCall)))
    assert len(rows) == 2 and all(r.result_status is None for r in rows)


# --- lewat API ------------------------------------------------------------------------------------------------


@pytest.fixture
def use_sources():
    def _use(sources):
        app.dependency_overrides[get_sources] = lambda: sources

    yield _use
    app.dependency_overrides.pop(get_sources, None)


def test_api_satu_sumber_crash_cek_tetap_tersimpan_data_terbatas(
    client, make_user, login, use_sources, caplog, db
):
    make_user("analyst", Role.ANALYST)
    use_sources([raising(A, RuntimeError(SECRET)), MockSource(V)])
    caplog.set_level(logging.DEBUG)

    resp = post(client, login, "1.1.1.1")

    assert resp.status_code == 201
    body = resp.json()
    abuse, vt = body["sources"]
    assert (abuse["status"], abuse["reason"], abuse["normalized_score"]) == (
        "ERROR",
        "INTERNAL_ERROR",
        None,
    )
    assert (
        vt["status"] == "OK_SIGNAL" and vt["normalized_score"] == 80
    )  # sumber lain tampil
    assert (body["assessment_status"], body["coverage"]) == ("DATA_TERBATAS", "1/2")
    assert body["risk_score"] is None and body["indication"] is None
    assert SECRET not in resp.text
    assert SECRET not in caplog.text
    (record,) = error_logs(caplog)
    assert "RuntimeError" in record.getMessage() and A in record.getMessage()
    db.expire_all()
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "ip_check")).one()
    assert audit.detail["sources"] == {A: "ERROR", V: "OK_SIGNAL"}
    assert SECRET not in json.dumps(audit.detail)


def test_api_value_error_dari_adapter_menggagalkan_keras(
    client, make_user, login, use_sources, db
):
    make_user("analyst", Role.ANALYST)
    use_sources([raising(A, ValueError("input ditolak lolos")), MockSource(V)])

    with pytest.raises(ValueError):
        post(client, login, "1.1.1.1")

    db.expire_all()
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "ip_check")
        )
        == 0
    )
