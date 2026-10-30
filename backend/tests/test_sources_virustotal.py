"""Adapter VirusTotal (TASK-02 Tahap 1): pemetaan status, pemetaan error, dan keamanan key.

Bab 3 dokumen riset tidak ada di repo; barisnya diturunkan dari butir 4 dan 5 rencana Tahap 1.
Semua respons berasal dari `MockTransport` dan fixture berlabel `nyata`/`simulasi`.
"""

import logging
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    SourceReason,
    SourceStatus,
)
from app.services.sources.virustotal import IP_URL, VirusTotalSource
from tests.sources_support import (
    FAKE_KEY,
    NOW,
    TIMEOUT_SECONDS,
    assert_score_invariants,
    client_for,
    fixture_text,
    leak_surfaces,
    raises,
    reply,
)

IP = "1.1.1.1"
NYATA = "virustotal_nyata_2026-10-29_118.25.6.39.json"
EPOCH = 1793236459


def make_source(responder):
    client, seen = client_for(responder)
    source = VirusTotalSource(
        client,
        SecretStr(FAKE_KEY),
        timeout_seconds=TIMEOUT_SECONDS,
        clock=lambda: NOW,
    )
    return source, seen


def fetch(responder, ip: str = IP):
    source, _ = make_source(responder)
    result = source.fetch(ip)
    assert_score_invariants(result)
    return result


def vt_body(stats: object, **attributes: object) -> dict:
    return {"data": {"attributes": {"last_analysis_stats": stats, **attributes}}}


# --- 200: OK_SIGNAL / OK_NO_SIGNAL / INSUFFICIENT_DATA ----------------------------


def test_respons_nyata_tanpa_deteksi_adalah_ok_no_signal_v_0():
    result = fetch(reply(200, fixture=NYATA))

    assert result.source == "virustotal"
    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.normalized_score == 0
    assert result.evidence_summary == {
        "malicious": 0,
        "suspicious": 0,
        "undetected": 38,
        "harmless": 54,
        "timeout": 0,
    }
    assert result.source_time == datetime.fromtimestamp(EPOCH, UTC)
    assert result.source_time_type == "last_analysis"
    assert result.retrieved_at == NOW
    assert result.http_status == 200
    assert isinstance(result.duration_ms, int) and result.duration_ms >= 0
    assert result.flags == ()  # ada yang menyatakan harmless: bukan NO_VENDOR_OPINION


def test_malicious_10_adalah_ok_signal_v_80():
    result = fetch(reply(200, fixture="virustotal_simulasi_malicious_10.json"))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == 80


@pytest.mark.parametrize(
    ("malicious", "suspicious", "expected"),
    [
        (1, 0, 8),
        (0, 1, 4),
        (2, 3, 28),
        (12, 0, 96),
        (12, 1, 100),  # tepat 100
        (13, 0, 100),  # dipangkas oleh min(100, ...)
        (60, 40, 100),
    ],
)
def test_rumus_v_adalah_min_100_dari_8_malicious_ditambah_4_suspicious(
    malicious, suspicious, expected
):
    stats = {
        "malicious": malicious,
        "suspicious": suspicious,
        "harmless": 10,
        "undetected": 10,
        "timeout": 0,
    }
    result = fetch(reply(200, body=vt_body(stats)))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == expected


def test_hanya_suspicious_sudah_cukup_menjadi_ok_signal():
    result = fetch(
        reply(200, body=vt_body({"malicious": 0, "suspicious": 2, "harmless": 5}))
    )

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == 8


def test_semua_undetected_adalah_ok_no_signal_dengan_flag_no_vendor_opinion():
    result = fetch(reply(200, fixture="virustotal_simulasi_all_undetected.json"))

    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.normalized_score == 0
    assert result.flags == (FLAG_NO_VENDOR_OPINION,)


def test_semua_timeout_adalah_insufficient_data_bukan_skor_0():
    result = fetch(reply(200, fixture="virustotal_simulasi_all_timeout.json"))

    assert result.status is SourceStatus.INSUFFICIENT_DATA
    assert result.normalized_score is None
    assert result.evidence_summary["timeout"] == 90
    assert result.flags == ()


def test_statistik_kosong_adalah_insufficient_data_bukan_skor_0():
    result = fetch(reply(200, fixture="virustotal_simulasi_stats_kosong.json"))

    assert result.status is SourceStatus.INSUFFICIENT_DATA
    assert result.normalized_score is None
    assert result.evidence_summary == {}


def test_kunci_statistik_yang_tidak_ada_dihitung_nol_dan_kunci_asing_diabaikan():
    stats = {"malicious": 1, "harmless": 3, "type-unsupported": 9, "failure": "x"}
    result = fetch(reply(200, body=vt_body(stats)))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == 8
    assert result.evidence_summary == {"malicious": 1, "harmless": 3}


# --- tanggal analisis -----------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [None, "1793236459", True, -1, 10**20, 1.5],
    ids=["null", "string", "bool", "negatif", "di-luar-rentang", "float"],
)
def test_last_analysis_date_tidak_sah_menjadi_null_tanpa_menggagalkan_skor(value):
    stats = {"malicious": 0, "harmless": 4}
    result = fetch(reply(200, body=vt_body(stats, last_analysis_date=value)))

    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.source_time is None
    assert result.source_time_type == "last_analysis"


def test_last_analysis_date_hilang_menjadi_null():
    result = fetch(reply(200, body=vt_body({"harmless": 4})))

    assert result.source_time is None


# --- 404 ------------------------------------------------------------------------


def test_404_not_found_error_adalah_no_record_bukan_skor_0():
    result = fetch(reply(404, fixture="virustotal_simulasi_tidak_ditemukan_404.json"))

    assert result.status is SourceStatus.NO_RECORD
    assert result.normalized_score is None
    assert result.reason is None
    assert result.http_status == 404


@pytest.mark.parametrize(
    "responder",
    [
        reply(404, body={"error": {"code": "SesuatuLain", "message": "x"}}),
        reply(404, body={"error": {"message": "tanpa kode"}}),
        reply(404, body={"error": "NotFoundError"}),
        reply(404, body=[]),
        reply(404, raw="<html>404 Not Found</html>"),
        reply(404, raw=""),
    ],
    ids=["kode-lain", "tanpa-kode", "error-bukan-objek", "body-list", "html", "kosong"],
)
def test_404_tanpa_kode_not_found_error_adalah_error_upstream(responder):
    # Bab 3: pastikan objek memang tidak ditemukan, bukan URL yang salah.
    result = fetch(responder)

    assert (result.status, result.reason) == (
        SourceStatus.ERROR,
        SourceReason.UPSTREAM,
    )
    assert result.http_status == 404


def test_not_found_error_pada_status_selain_404_tidak_dianggap_no_record():
    result = fetch(reply(200, fixture="virustotal_simulasi_tidak_ditemukan_404.json"))

    assert result.status is SourceStatus.ERROR
    assert result.reason is SourceReason.INVALID_RESPONSE


# --- 200 tetapi isi tidak sah: ERROR + INVALID_RESPONSE ---------------------------


@pytest.mark.parametrize(
    "responder",
    [
        reply(200, fixture="virustotal_simulasi_field_hilang.json"),
        reply(200, body=vt_body(None)),
        reply(200, body=vt_body([])),
        reply(200, body=vt_body("banyak")),
        reply(200, body=vt_body({"malicious": "5"})),
        reply(200, body=vt_body({"malicious": 5.0})),
        reply(200, body=vt_body({"malicious": True})),
        reply(200, body=vt_body({"harmless": -3})),
        reply(200, body=vt_body({"harmless": None})),
        reply(200, body={"data": {"attributes": []}}),
        reply(200, body={"data": []}),
        reply(200, body={"bukan": "data"}),
        reply(200, body=[1]),
        reply(200, body=None),
        reply(200, raw=""),
        reply(200, raw=fixture_text("simulasi_json_rusak.txt")),
    ],
    ids=[
        "stats-hilang",
        "stats-null",
        "stats-list",
        "stats-string",
        "nilai-string",
        "nilai-float",
        "nilai-bool",
        "nilai-negatif",
        "nilai-null",
        "attributes-bukan-objek",
        "data-bukan-objek",
        "tanpa-data",
        "body-list",
        "body-null",
        "body-kosong",
        "json-rusak",
    ],
)
def test_respons_200_tidak_sah_adalah_error_invalid_response_bukan_skor_0(responder):
    result = fetch(responder)

    assert result.status is SourceStatus.ERROR
    assert result.reason is SourceReason.INVALID_RESPONSE
    assert result.normalized_score is None
    assert result.http_status == 200


# --- error HTTP -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "fixture"),
    [(401, "virustotal_simulasi_401.json"), (403, "virustotal_simulasi_403.json")],
)
def test_401_dan_403_adalah_error_auth(status, fixture):
    result = fetch(reply(status, fixture=fixture))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.AUTH)
    assert result.http_status == status


def test_status_dibaca_sebelum_body_jadi_body_rusak_pada_401_tetap_auth():
    result = fetch(reply(401, raw="<html>bukan json</html>"))

    assert result.reason is SourceReason.AUTH


def test_429_adalah_rate_limit_dan_menyimpan_retry_after():
    result = fetch(
        reply(
            429, fixture="virustotal_simulasi_429.json", headers={"Retry-After": "60"}
        )
    )

    assert (result.status, result.reason) == (
        SourceStatus.ERROR,
        SourceReason.RATE_LIMIT,
    )
    assert result.http_status == 429
    assert result.retry_after_seconds == 60


def test_429_tanpa_retry_after_menyimpan_null():
    result = fetch(reply(429, fixture="virustotal_simulasi_429.json"))

    assert result.reason is SourceReason.RATE_LIMIT
    assert result.retry_after_seconds is None


@pytest.mark.parametrize("status", [400, 422, 500, 502, 503, 504, 302, 418], ids=str)
def test_status_lain_adalah_error_upstream(status):
    result = fetch(reply(status, body={"error": {"code": "TransientError"}}))

    assert (result.status, result.reason) == (
        SourceStatus.ERROR,
        SourceReason.UPSTREAM,
    )
    assert result.http_status == status


def test_timeout_adalah_error_timeout_tanpa_status_http():
    result = fetch(raises(httpx.ConnectTimeout))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.TIMEOUT)
    assert result.http_status is None
    assert result.retrieved_at == NOW


@pytest.mark.parametrize("exc_type", [httpx.ConnectError, httpx.RemoteProtocolError])
def test_koneksi_gagal_adalah_error_upstream(exc_type):
    result = fetch(raises(exc_type))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.UPSTREAM)


def test_redirect_tidak_diikuti_dan_dianggap_upstream():
    # httpx meneruskan header kustom (x-apikey) ke tujuan redirect; adapter tidak boleh mengikutinya.
    source, seen = make_source(
        reply(302, body={}, headers={"Location": "https://pihak-lain.example/"})
    )

    result = source.fetch(IP)

    assert result.reason is SourceReason.UPSTREAM
    assert len(seen) == 1


# --- bentuk request ----------------------------------------------------------------


def test_request_memakai_header_x_apikey_dan_ip_di_path():
    source, seen = make_source(reply(200, fixture=NYATA))

    source.fetch(" 1.1.1.1 ")  # spasi dipangkas; yang dikirim IP kanonik

    (request,) = seen
    assert request.method == "GET"
    assert str(request.url) == IP_URL.format(ip="1.1.1.1")
    assert request.url.query == b""
    assert request.headers["x-apikey"] == FAKE_KEY
    assert request.headers["Accept"] == "application/json"


def test_timeout_dari_config_dipakai_di_setiap_request():
    source, seen = make_source(reply(200, fixture=NYATA))

    source.fetch(IP)

    assert seen[0].extensions["timeout"] == {
        "connect": TIMEOUT_SECONDS,
        "read": TIMEOUT_SECONDS,
        "write": TIMEOUT_SECONDS,
        "pool": TIMEOUT_SECONDS,
    }


@pytest.mark.parametrize(
    "ip",
    ["10.0.0.1", "127.0.0.1", "::1", "abc", "1.1.1.1/../files", "", "192.0.2.1"],
)
def test_ip_tidak_valid_atau_tidak_publik_tidak_memicu_request(ip):
    # IP masuk ke path URL VirusTotal; input seperti "1.1.1.1/../files" tidak boleh lolos.
    source, seen = make_source(reply(200, fixture=NYATA))

    with pytest.raises(ValueError):
        source.fetch(ip)

    assert seen == []


# --- key tidak boleh bocor -----------------------------------------------------------


@pytest.mark.parametrize(
    "responder",
    [
        reply(200, fixture=NYATA),
        reply(200, raw="bukan json"),
        reply(401, fixture="virustotal_simulasi_401.json"),
        reply(403, fixture="virustotal_simulasi_403.json"),
        reply(404, fixture="virustotal_simulasi_tidak_ditemukan_404.json"),
        reply(
            429, fixture="virustotal_simulasi_429.json", headers={"Retry-After": "9"}
        ),
        reply(503, body={}),
        raises(httpx.ReadTimeout),
        raises(httpx.ConnectError),
    ],
    ids=["200", "200-rusak", "401", "403", "404", "429", "503", "timeout", "koneksi"],
)
def test_key_tidak_muncul_di_url_log_hasil_maupun_repr_adapter(responder, caplog):
    caplog.set_level(logging.DEBUG)
    source, seen = make_source(responder)

    result = source.fetch(IP)

    assert FAKE_KEY not in str(seen[0].url)
    assert FAKE_KEY not in caplog.text
    assert FAKE_KEY in seen[0].headers["x-apikey"]  # kontrol: header memang membawanya
    for surface in leak_surfaces(result, source):
        assert FAKE_KEY not in surface


# --- data kontak dan data besar tidak boleh ikut --------------------------------------


def test_whois_rdap_dan_last_analysis_results_tidak_disalin_ke_hasil():
    body = vt_body(
        {"malicious": 1, "harmless": 3},
        last_analysis_date=EPOCH,
        whois="WHOIS-PENANDA",
        rdap={"entities": [{"vcardArray": "RDAP-PENANDA"}]},
        last_analysis_results={"VendorX": {"result": "HASIL-PENANDA"}},
        as_owner="PEMILIK-PENANDA",
    )
    result = fetch(reply(200, body=body))

    assert set(result.evidence_summary) == {"malicious", "harmless"}
    for marker in ("WHOIS-PENANDA", "RDAP-PENANDA", "HASIL-PENANDA", "PEMILIK-PENANDA"):
        assert marker not in repr(result)
