"""Adapter mock sumber reputasi (TASK-02 Tahap 1): tabel IP demo, label simulasi, tanpa jaringan.

Yang dites di sini HASIL PER SUMBER. Skor gabungan, label, dan assessment_status
(85,5 / 49,1 / `COMPLETE` / ...) adalah keluaran Tahap 2.
"""

import socket

import pytest

from app.services.sources.abuseipdb import SOURCE_NAME as ABUSE
from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    FLAG_SUMBER_SIMULASI,
    SourceReason,
    SourceStatus,
)
from app.services.sources.mock import DEMO_SCENARIOS, MockSource
from app.services.sources.virustotal import SOURCE_NAME as VT
from tests.sources_support import NOW, assert_score_invariants

OK = SourceStatus.OK_SIGNAL
NO_SIGNAL = SourceStatus.OK_NO_SIGNAL
ERROR = SourceStatus.ERROR

# (ip, status A, skor A, status V, skor V) sesuai tabel IP demo di rencana Tahap 1.
BARIS_TABEL = [
    ("1.1.1.1", OK, 90, OK, 80),
    ("1.0.0.1", OK, 90, NO_SIGNAL, 0),
    ("8.8.8.8", OK, 90, ERROR, None),
    ("8.8.4.4", ERROR, None, SourceStatus.NO_RECORD, None),
    ("9.9.9.9", OK, 90, OK, 80),
    ("149.112.112.112", NO_SIGNAL, 0, NO_SIGNAL, 0),
    ("208.67.222.222", NO_SIGNAL, 0, SourceStatus.INSUFFICIENT_DATA, None),
]
IP_DI_LUAR_TABEL = "93.184.216.34"


def fetch_both(ip: str):
    abuse = MockSource(ABUSE, clock=lambda: NOW).fetch(ip)
    vt = MockSource(VT, clock=lambda: NOW).fetch(ip)
    for result in (abuse, vt):
        assert_score_invariants(result)
    return abuse, vt


@pytest.fixture(autouse=True)
def tanpa_jaringan(monkeypatch):
    def terlarang(*args, **kwargs):
        raise AssertionError("adapter mock tidak boleh membuka koneksi jaringan")

    monkeypatch.setattr(socket.socket, "connect", terlarang)
    monkeypatch.setattr(socket, "getaddrinfo", terlarang)


@pytest.mark.parametrize(
    ("ip", "status_a", "skor_a", "status_v", "skor_v"), BARIS_TABEL
)
def test_baris_tabel_ip_demo(ip, status_a, skor_a, status_v, skor_v):
    abuse, vt = fetch_both(ip)

    assert (abuse.source, abuse.status, abuse.normalized_score) == (
        ABUSE,
        status_a,
        skor_a,
    )
    assert (vt.source, vt.status, vt.normalized_score) == (VT, status_v, skor_v)


def test_tabel_di_test_mencakup_semua_ip_demo():
    assert {baris[0] for baris in BARIS_TABEL} == set(DEMO_SCENARIOS)


def test_sumber_error_menyebut_alasan_timeout_dan_tidak_pernah_skor():
    _, vt = fetch_both("8.8.8.8")
    abuse, _ = fetch_both("8.8.4.4")

    for result in (vt, abuse):
        assert (result.status, result.reason) == (ERROR, SourceReason.TIMEOUT)
        assert result.normalized_score is None


def test_ip_whitelisted_membawa_bukti_is_whitelisted_true():
    abuse, _ = fetch_both("9.9.9.9")

    assert abuse.evidence_summary["isWhitelisted"] is True


def test_semua_undetected_membawa_flag_no_vendor_opinion():
    _, vt = fetch_both("149.112.112.112")

    assert FLAG_NO_VENDOR_OPINION in vt.flags


def test_hasil_vt_malicious_10_dihitung_oleh_rumus_adapter_asli():
    _, vt = fetch_both("1.1.1.1")

    assert vt.evidence_summary["malicious"] == 10
    assert vt.normalized_score == 80


def test_ip_di_luar_tabel_mendapat_hasil_bawaan_kedua_sumber_ok_no_signal():
    abuse, vt = fetch_both(IP_DI_LUAR_TABEL)

    assert (abuse.status, abuse.normalized_score) == (NO_SIGNAL, 0)
    assert (vt.status, vt.normalized_score) == (NO_SIGNAL, 0)
    assert FLAG_NO_VENDOR_OPINION not in vt.flags


@pytest.mark.parametrize("ip", [*DEMO_SCENARIOS, IP_DI_LUAR_TABEL])
def test_setiap_hasil_mock_berflag_simulasi_dan_bukan_data_nyata(ip):
    for result in fetch_both(ip):
        assert FLAG_SUMBER_SIMULASI in result.flags
        assert result.evidence_summary["simulasi"] is True
        # Bukan hasil panggilan HTTP: tidak ada status/durasi, dan tidak berasal dari cache.
        assert result.http_status is None
        assert result.duration_ms is None
        assert result.from_cache is False
        assert result.retrieved_at == NOW


def test_hasil_mock_deterministik():
    assert fetch_both("1.1.1.1") == fetch_both("1.1.1.1")


@pytest.mark.parametrize("ip", ["10.0.0.1", "127.0.0.1", "::1", "abc", ""])
def test_ip_tidak_valid_atau_tidak_publik_ditolak(ip):
    with pytest.raises(ValueError):
        MockSource(ABUSE).fetch(ip)


def test_nama_sumber_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        MockSource("otx")
