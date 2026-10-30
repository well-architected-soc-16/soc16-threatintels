"""Adapter AbuseIPDB (TASK-02 Tahap 1): pemetaan status, pemetaan error, dan keamanan key.

Bab 3 dokumen riset tidak ada di repo; barisnya diturunkan dari butir 3 dan 5 rencana Tahap 1.
Semua respons berasal dari `MockTransport` dan fixture berlabel `nyata`/`simulasi`.
"""

import logging
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.services.sources.abuseipdb import CHECK_URL, AbuseIpdbSource
from app.services.sources.base import SourceReason, SourceStatus
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
NYATA = "abuseipdb_nyata_2026-10-29_118.25.6.39.json"


def make_source(responder, *, max_age_days: int = 30):
    client, seen = client_for(responder)
    source = AbuseIpdbSource(
        client,
        SecretStr(FAKE_KEY),
        max_age_days=max_age_days,
        timeout_seconds=TIMEOUT_SECONDS,
        clock=lambda: NOW,
    )
    return source, seen


def fetch(responder, ip: str = IP):
    source, _ = make_source(responder)
    result = source.fetch(ip)
    assert_score_invariants(result)
    return result


# --- 200: OK_SIGNAL / OK_NO_SIGNAL -------------------------------------------


def test_respons_nyata_skor_7_adalah_ok_signal_walau_nol_laporan():
    result = fetch(reply(200, fixture=NYATA))

    assert result.source == "abuseipdb"
    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == 7
    assert result.evidence_summary == {
        "abuseConfidenceScore": 7,
        "totalReports": 0,
        "numDistinctUsers": 0,
        "lastReportedAt": "2026-09-17T22:17:21+00:00",
        "isWhitelisted": False,
    }
    assert result.source_time == datetime(2026, 9, 17, 22, 17, 21, tzinfo=UTC)
    assert result.source_time_type == "last_report"
    assert result.retrieved_at == NOW
    assert result.http_status == 200
    assert isinstance(result.duration_ms, int) and result.duration_ms >= 0
    assert result.flags == ()


def test_skor_90_adalah_ok_signal():
    result = fetch(reply(200, fixture="abuseipdb_simulasi_skor_90.json"))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.normalized_score == 90


def test_skor_0_dengan_laporan_adalah_ok_no_signal():
    result = fetch(reply(200, fixture="abuseipdb_simulasi_skor_0_ada_laporan.json"))

    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.normalized_score == 0
    assert result.evidence_summary["totalReports"] == 5
    assert result.source_time == datetime(2026, 10, 20, 8, 30, tzinfo=UTC)


def test_skor_0_dan_nol_laporan_adalah_ok_no_signal_bukan_no_record():
    result = fetch(reply(200, fixture="abuseipdb_simulasi_skor_0_nol_laporan.json"))

    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.normalized_score == 0
    assert result.evidence_summary["totalReports"] == 0
    # isWhitelisted bisa null di API; tetap null, bukan False.
    assert result.evidence_summary["isWhitelisted"] is None


def test_last_reported_at_null_tidak_menggagalkan_skor():
    result = fetch(reply(200, fixture="abuseipdb_simulasi_skor_0_nol_laporan.json"))

    assert result.status is SourceStatus.OK_NO_SIGNAL
    assert result.source_time is None
    assert result.source_time_type == "last_report"
    assert result.evidence_summary["lastReportedAt"] is None


def test_last_reported_at_tidak_valid_menjadi_null_tanpa_menggagalkan_skor():
    body = {"data": {"abuseConfidenceScore": 12, "lastReportedAt": "kemarin"}}
    result = fetch(reply(200, body=body))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.source_time is None
    assert result.evidence_summary["lastReportedAt"] is None


@pytest.mark.parametrize("score", [0, 1, 50, 100])
def test_batas_skor_yang_sah_diterima(score):
    result = fetch(reply(200, body={"data": {"abuseConfidenceScore": score}}))

    assert result.normalized_score == score
    expected = SourceStatus.OK_SIGNAL if score else SourceStatus.OK_NO_SIGNAL
    assert result.status is expected


# --- 200 tetapi isi tidak sah: ERROR + INVALID_RESPONSE -----------------------


@pytest.mark.parametrize(
    "responder",
    [
        reply(200, fixture="abuseipdb_simulasi_field_hilang.json"),
        reply(200, body={"data": {"abuseConfidenceScore": "7"}}),
        reply(200, body={"data": {"abuseConfidenceScore": 7.0}}),
        reply(200, body={"data": {"abuseConfidenceScore": True}}),
        reply(200, body={"data": {"abuseConfidenceScore": None}}),
        reply(200, body={"data": {"abuseConfidenceScore": -1}}),
        reply(200, body={"data": {"abuseConfidenceScore": 101}}),
        reply(200, body={"data": []}),
        reply(200, body={"bukan": "data"}),
        reply(200, body=[1, 2, 3]),
        reply(200, body=None),
        reply(200, raw=""),
        reply(200, raw="<html>gateway</html>"),
        reply(200, raw=fixture_text("simulasi_json_rusak.txt")),
    ],
    ids=[
        "field-hilang",
        "skor-string",
        "skor-float",
        "skor-bool",
        "skor-null",
        "skor-negatif",
        "skor-101",
        "data-bukan-objek",
        "tanpa-data",
        "body-list",
        "body-null",
        "body-kosong",
        "bukan-json",
        "json-rusak",
    ],
)
def test_respons_200_tidak_sah_adalah_error_invalid_response_bukan_skor_0(responder):
    result = fetch(responder)

    assert result.status is SourceStatus.ERROR
    assert result.reason is SourceReason.INVALID_RESPONSE
    assert result.normalized_score is None
    assert result.http_status == 200


# --- error HTTP ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "fixture"),
    [(401, "abuseipdb_simulasi_401.json"), (403, "abuseipdb_simulasi_403.json")],
)
def test_401_dan_403_adalah_error_auth(status, fixture):
    result = fetch(reply(status, fixture=fixture))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.AUTH)
    assert result.http_status == status


def test_header_rate_limit_dibaca_untuk_sukses_dan_error():
    ok = fetch(
        reply(
            200,
            fixture=NYATA,
            headers={"X-RateLimit-Reset": "1793318400", "X-RateLimit-Remaining": "999"},
        )
    )
    limited = fetch(
        reply(
            429,
            fixture="abuseipdb_simulasi_429.json",
            headers={"X-RateLimit-Reset": "1793318400", "X-RateLimit-Remaining": "0"},
        )
    )

    for result, remaining in ((ok, 999), (limited, 0)):
        assert result.rate_limit_reset == datetime(2026, 10, 30, 0, 0, tzinfo=UTC)
        assert result.rate_limit_remaining == remaining


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-RateLimit-Reset": "besok", "X-RateLimit-Remaining": "banyak"},
        {"X-RateLimit-Reset": "-5", "X-RateLimit-Remaining": "-1"},
        {"X-RateLimit-Reset": "99999999999999999999"},
    ],
    ids=["tanpa-header", "bukan-angka", "negatif", "di-luar-rentang"],
)
def test_header_rate_limit_tidak_sah_diabaikan_tanpa_menggagalkan_hasil(headers):
    result = fetch(reply(200, fixture=NYATA, headers=headers))

    assert result.status is SourceStatus.OK_SIGNAL
    assert result.rate_limit_reset is None
    assert result.rate_limit_remaining is None


def test_status_dibaca_sebelum_body_jadi_body_rusak_pada_401_tetap_auth():
    result = fetch(reply(401, raw="<html>bukan json</html>"))

    assert result.reason is SourceReason.AUTH


def test_429_adalah_rate_limit_dan_menyimpan_retry_after():
    result = fetch(
        reply(
            429, fixture="abuseipdb_simulasi_429.json", headers={"Retry-After": "3600"}
        )
    )

    assert (result.status, result.reason) == (
        SourceStatus.ERROR,
        SourceReason.RATE_LIMIT,
    )
    assert result.http_status == 429
    assert result.retry_after_seconds == 3600


@pytest.mark.parametrize(
    "headers",
    [{}, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, {"Retry-After": "-5"}],
    ids=["tanpa-header", "http-date", "negatif"],
)
def test_429_tanpa_retry_after_berupa_detik_menyimpan_null(headers):
    result = fetch(reply(429, fixture="abuseipdb_simulasi_429.json", headers=headers))

    assert result.reason is SourceReason.RATE_LIMIT
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    "status", [400, 404, 422, 500, 502, 503, 504, 302, 418], ids=str
)
def test_status_lain_adalah_error_upstream(status):
    result = fetch(reply(status, body={"errors": [{"detail": "x", "status": status}]}))

    assert (result.status, result.reason) == (
        SourceStatus.ERROR,
        SourceReason.UPSTREAM,
    )
    assert result.http_status == status


def test_timeout_adalah_error_timeout_tanpa_status_http():
    result = fetch(raises(httpx.ReadTimeout))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.TIMEOUT)
    assert result.http_status is None
    assert result.retrieved_at == NOW


@pytest.mark.parametrize("exc_type", [httpx.ConnectError, httpx.RemoteProtocolError])
def test_koneksi_gagal_adalah_error_upstream(exc_type):
    result = fetch(raises(exc_type))

    assert (result.status, result.reason) == (SourceStatus.ERROR, SourceReason.UPSTREAM)


def test_redirect_tidak_diikuti_dan_dianggap_upstream():
    # httpx meneruskan header kustom (Key) ke tujuan redirect; adapter tidak boleh mengikutinya.
    source, seen = make_source(
        reply(302, body={}, headers={"Location": "https://pihak-lain.example/"})
    )

    result = source.fetch(IP)

    assert result.reason is SourceReason.UPSTREAM
    assert len(seen) == 1


# --- bentuk request ---------------------------------------------------------------


def test_request_memakai_header_key_dan_parameter_dari_config():
    source, seen = make_source(reply(200, fixture=NYATA), max_age_days=45)

    source.fetch(" 1.1.1.1 ")  # spasi dipangkas; yang dikirim IP kanonik

    (request,) = seen
    assert request.method == "GET"
    assert str(request.url.copy_with(query=None)) == CHECK_URL
    assert dict(request.url.params) == {"ipAddress": "1.1.1.1", "maxAgeInDays": "45"}
    assert request.headers["Key"] == FAKE_KEY
    assert request.headers["Accept"] == "application/json"
    assert (
        "verbose" not in request.url.params
    )  # tidak meminta komentar laporan individual


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
    "ip", ["10.0.0.1", "127.0.0.1", "::1", "abc", "1.1.1.1/../x", "", "192.0.2.1"]
)
def test_ip_tidak_valid_atau_tidak_publik_tidak_memicu_request(ip):
    source, seen = make_source(reply(200, fixture=NYATA))

    with pytest.raises(ValueError):
        source.fetch(ip)

    assert seen == []


# --- key tidak boleh bocor ---------------------------------------------------------


@pytest.mark.parametrize(
    "responder",
    [
        reply(200, fixture=NYATA),
        reply(200, raw="bukan json"),
        reply(401, fixture="abuseipdb_simulasi_401.json"),
        reply(429, fixture="abuseipdb_simulasi_429.json", headers={"Retry-After": "9"}),
        reply(500, body={}),
        raises(httpx.ReadTimeout),
        raises(httpx.ConnectError),
    ],
    ids=["200", "200-rusak", "401", "429", "500", "timeout", "koneksi"],
)
def test_key_tidak_muncul_di_url_log_hasil_maupun_repr_adapter(responder, caplog):
    caplog.set_level(logging.DEBUG)
    source, seen = make_source(responder)

    result = source.fetch(IP)

    assert FAKE_KEY not in str(seen[0].url)
    assert FAKE_KEY not in caplog.text
    assert FAKE_KEY in seen[0].headers["Key"]  # kontrol: header memang membawanya
    for surface in leak_surfaces(result, source):
        assert FAKE_KEY not in surface


# --- bukti hanya dari field yang dikenal -----------------------------------------


def test_field_lain_dari_respons_tidak_disalin_ke_hasil():
    body = {
        "data": {
            "abuseConfidenceScore": 40,
            "totalReports": 2,
            "isp": "ISP-PENANDA",
            "domain": "penanda.example",
            "reports": [{"comment": "KOMENTAR-PENANDA", "reporterId": 7}],
        }
    }
    result = fetch(reply(200, body=body))

    assert set(result.evidence_summary) == {
        "abuseConfidenceScore",
        "totalReports",
        "numDistinctUsers",
        "lastReportedAt",
        "isWhitelisted",
    }
    for marker in ("ISP-PENANDA", "penanda.example", "KOMENTAR-PENANDA"):
        assert marker not in repr(result)
