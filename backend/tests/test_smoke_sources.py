"""Skrip smoke `scripts.smoke_sources` (TASK-02 Tahap 4), TANPA jaringan.

Semua request lewat `httpx.MockTransport` dengan key palsu; test ini tidak pernah memanggil API
AbuseIPDB atau VirusTotal. Yang dibuktikan: skrip lewat `SourceGateway` yang sama (kuota, cache,
`source_calls`), menolak mode mock dan IP tak valid sebelum request apa pun, dan tidak pernah
mencetak key, baik di jalur sukses maupun error.
"""

import io
import logging
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SourceCall
from app.services.sources.factory import build_gateways
from app.services.sources.gateway import SourceGateway
from scripts import smoke_sources
from tests.sources_support import (
    FAKE_KEY,
    NYATA_ABUSEIPDB,
    NYATA_VIRUSTOTAL,
    FakeSource,
    live_adapters_with_requests,
    make_gateway,
    raises,
    reply,
)

IP = "118.25.6.39"
# Nama header autentikasi tidak boleh muncul di keluaran (key dikirim hanya lewat header).
HEADER_NAMES = ("x-apikey", "authorization")


@pytest.fixture(autouse=True)
def _bersih(db):
    """`db` men-TRUNCATE semua tabel (termasuk source_cache dan source_calls) sebelum tiap test."""


def gateways_for(engine, abuse_responder, vt_responder):
    adapters, abuse_seen, vt_seen = live_adapters_with_requests(
        abuse_responder, vt_responder
    )
    gateways = [make_gateway(adapter, engine) for adapter in adapters]
    return gateways, abuse_seen, vt_seen


def sukses(engine):
    return gateways_for(
        engine,
        reply(200, fixture=NYATA_ABUSEIPDB),
        reply(200, fixture=NYATA_VIRUSTOTAL),
    )


def run_smoke(gateways, ip: str = IP) -> tuple[int, str]:
    out = io.StringIO()
    code = smoke_sources.run(ip, gateways, out)
    return code, out.getvalue()


def assert_no_secret(text: str) -> None:
    assert FAKE_KEY not in text
    lowered = text.lower()
    for name in HEADER_NAMES:
        assert name not in lowered


def live_calls(engine) -> list[SourceCall]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(SourceCall)
                .where(SourceCall.mode == "live")
                .order_by(SourceCall.id)
            )
        )


# --- jalur sukses ---------------------------------------------------------------------------


def test_sukses_mencetak_ringkasan_per_sumber_dan_exit_0(engine):
    gateways, _, _ = sukses(engine)

    code, text = run_smoke(gateways)

    assert code == 0
    assert f"ip: {IP}" in text
    assert "[abuseipdb]" in text and "[virustotal]" in text
    for label in (
        "http_status",
        "status",
        "reason",
        "skor_ternormalisasi",
        "durasi_ms",
        "rate_limit_remaining",
        "dari_cache",
        "bukti",
    ):
        assert label in text
    assert "200" in text
    assert "Semua sumber menjawab." in text
    assert_no_secret(text)


def test_sukses_lewat_gateway_dicatat_di_source_calls_dan_dihitung(engine):
    gateways, abuse_seen, vt_seen = sukses(engine)

    run_smoke(gateways)

    calls = live_calls(engine)
    assert [(c.source, c.mode, c.http_status) for c in calls] == [
        ("abuseipdb", "live", 200),
        ("virustotal", "live", 200),
    ]
    # reservasi sudah diselesaikan (bukan baris menggantung)
    assert all(c.result_status is not None for c in calls)
    assert len(abuse_seen) == len(vt_seen) == 1


def test_menjalankan_dua_kali_kedua_dari_cache_tanpa_request_baru(engine):
    gateways, abuse_seen, vt_seen = sukses(engine)

    run_smoke(gateways)
    code, text = run_smoke(gateways)

    assert code == 0
    assert text.count("ya (tanpa request)") == 2
    assert len(abuse_seen) == len(vt_seen) == 1
    assert len(live_calls(engine)) == 2  # tidak bertambah
    assert_no_secret(text)


def test_sumber_yang_melewati_kuota_internal_dilaporkan_bermasalah(engine):
    from app.services.sources.quota import QuotaPolicy

    adapters, abuse_seen, _ = live_adapters_with_requests(
        reply(200, fixture=NYATA_ABUSEIPDB), reply(200, fixture=NYATA_VIRUSTOTAL)
    )
    gateways = [
        make_gateway(adapters[0], engine, policy=QuotaPolicy(daily=0)),
        make_gateway(adapters[1], engine),
    ]

    code, text = run_smoke(gateways)

    assert code == 1
    assert "SKIPPED" in text and "QUOTA_INTERNAL" in text
    assert "1 sumber bermasalah." in text
    assert abuse_seen == []  # kuota habis: tidak ada request keluar
    assert_no_secret(text)


# --- jalur error: key tidak boleh bocor ------------------------------------------------------

ERROR_CASES = {
    "401": (
        reply(401, fixture="abuseipdb_simulasi_401.json"),
        reply(401, fixture="virustotal_simulasi_401.json"),
        "AUTH",
    ),
    "403": (
        reply(403, fixture="abuseipdb_simulasi_403.json"),
        reply(403, fixture="virustotal_simulasi_403.json"),
        "AUTH",
    ),
    "429": (
        reply(
            429,
            fixture="abuseipdb_simulasi_429.json",
            headers={"Retry-After": "30"},
        ),
        reply(
            429,
            fixture="virustotal_simulasi_429.json",
            headers={"Retry-After": "30"},
        ),
        "RATE_LIMIT",
    ),
    "timeout": (raises(httpx.ReadTimeout), raises(httpx.ReadTimeout), "TIMEOUT"),
    "koneksi": (raises(httpx.ConnectError), raises(httpx.ConnectError), "UPSTREAM"),
    "json_rusak": (
        reply(200, raw="{bukan json"),
        reply(200, raw="{bukan json"),
        "INVALID_RESPONSE",
    ),
}


@pytest.mark.parametrize("case", ERROR_CASES)
def test_error_tidak_membocorkan_key_dan_exit_1(engine, case):
    abuse_responder, vt_responder, reason = ERROR_CASES[case]
    gateways, _, _ = gateways_for(engine, abuse_responder, vt_responder)

    code, text = run_smoke(gateways)

    assert code == 1
    assert text.count("ERROR") >= 2
    assert reason in text
    assert "2 sumber bermasalah." in text
    assert_no_secret(text)


def test_429_mencetak_retry_after_dari_header(engine):
    abuse, vt, _ = ERROR_CASES["429"]
    gateways, _, _ = gateways_for(engine, abuse, vt)

    _, text = run_smoke(gateways)

    assert "retry_after_detik    : 30" in text


def test_exception_tak_terduga_hanya_mencetak_nama_kelas(engine):
    def boom(ip: str):
        raise RuntimeError(f"bocor {FAKE_KEY}")

    gateway = make_gateway(FakeSource("abuseipdb", respond=boom), engine)

    code, text = run_smoke([gateway])

    assert code == 1
    assert "gagal tak terduga: RuntimeError" in text
    assert_no_secret(text)


def test_log_httpx_tidak_memuat_key(engine, caplog):
    gateways, _, _ = sukses(engine)

    with caplog.at_level(logging.DEBUG):
        run_smoke(gateways)

    assert FAKE_KEY not in caplog.text


# --- main: penolakan sebelum request apa pun --------------------------------------------------


@pytest.fixture
def patched_main(monkeypatch, engine):
    """Pasang pengaturan `live` palsu dan gateway MockTransport; kembalikan penampung request."""
    state = SimpleNamespace(mode="live")
    gateways, abuse_seen, vt_seen = sukses(engine)
    monkeypatch.setattr(
        smoke_sources,
        "get_settings",
        lambda: SimpleNamespace(sources_mode=state.mode),
    )
    monkeypatch.setattr(smoke_sources, "get_engine", lambda: engine)
    monkeypatch.setattr(smoke_sources, "build_gateways", lambda eng: gateways)
    state.requests = (abuse_seen, vt_seen)
    return state


def test_main_live_menjalankan_ip_bawaan(patched_main, engine, capsys):
    code = smoke_sources.main([])

    out = capsys.readouterr()
    assert code == 0
    assert f"ip: {smoke_sources.DEFAULT_IP}" in out.out
    assert [len(seen) for seen in patched_main.requests] == [1, 1]
    assert_no_secret(out.out + out.err)


def test_main_menerima_argumen_ip(patched_main, capsys):
    code = smoke_sources.main(["--ip", "8.8.8.8"])

    assert code == 0
    assert "ip: 8.8.8.8" in capsys.readouterr().out


@pytest.mark.parametrize(
    "ip", ["10.0.0.1", "127.0.0.1", "192.168.1.1", "2001:db8::1", "bukan-ip", ""]
)
def test_main_menolak_ip_tak_valid_tanpa_request_atau_kuota(
    patched_main, engine, capsys, ip
):
    code = smoke_sources.main(["--ip", ip])

    out = capsys.readouterr().out
    assert code == 2
    assert "tidak ada request yang dikirim" in out
    assert [len(seen) for seen in patched_main.requests] == [0, 0]
    assert live_calls(engine) == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SourceCall)) == 0


def test_main_menolak_mode_mock_tanpa_request_atau_kuota(patched_main, engine, capsys):
    patched_main.mode = "mock"

    code = smoke_sources.main(["--ip", IP])

    out = capsys.readouterr().out
    assert code == 2
    assert "bukan 'live'" in out
    assert [len(seen) for seen in patched_main.requests] == [0, 0]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SourceCall)) == 0


# --- build_gateways: sumber yang sama dengan API ---------------------------------------------


def test_build_gateways_mock_mengembalikan_gateway_urut_tetap(engine):
    gateways = build_gateways(engine)

    assert [g.name for g in gateways] == ["abuseipdb", "virustotal"]
    assert all(isinstance(g, SourceGateway) for g in gateways)
