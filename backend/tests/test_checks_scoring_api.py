"""Kontrak respons `POST/GET /checks` setelah adapter tersambung (TASK-02 Tahap 2).

Mode mock (default test) dipakai untuk tabel IP demo; adapter asli di atas `MockTransport`
dipakai untuk data nyata dan jalur error, lewat override dependency `get_sources`.
"""

import json
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.core.timeutil import to_wib_iso
from app.main import app
from app.models import AuditLog, IpCheck, Role
from app.services.sources.factory import get_sources
from tests.sources_support import (
    FAKE_KEY,
    NOW,
    NYATA_ABUSEIPDB,
    NYATA_VIRUSTOTAL,
    live_adapters,
    post,
    raises,
    reply,
)

CHECKS = "/api/v1/checks"
NYATA_A = NYATA_ABUSEIPDB
NYATA_V = NYATA_VIRUSTOTAL


@pytest.fixture
def use_sources():
    def _use(sources):
        app.dependency_overrides[get_sources] = lambda: sources

    yield _use
    app.dependency_overrides.pop(get_sources, None)


# --- tabel IP demo lewat API ----------------------------------------------------------

DEMO = [
    # ip, risk_score di respons, assessment_status, coverage, indication, flags
    ("1.1.1.1", 85.5, "COMPLETE", "2/2", "SANGAT_TINGGI", ["SUMBER_SIMULASI"]),
    (
        "1.0.0.1",
        49.1,
        "COMPLETE",
        "2/2",
        "PERLU_PEMERIKSAAN",
        ["HASIL_BERBEDA", "SUMBER_SIMULASI"],
    ),
    ("8.8.8.8", None, "DATA_TERBATAS", "1/2", None, ["SUMBER_SIMULASI"]),
    ("8.8.4.4", None, "TIDAK_TERSEDIA", "0/2", None, ["SUMBER_SIMULASI"]),
    (
        "9.9.9.9",
        85.5,
        "COMPLETE",
        "2/2",
        "SANGAT_TINGGI",
        ["WHITELISTED", "SUMBER_SIMULASI"],
    ),
    (
        "149.112.112.112",
        0.0,
        "COMPLETE",
        "2/2",
        "RENDAH",
        ["NO_VENDOR_OPINION", "SUMBER_SIMULASI"],
    ),
    ("208.67.222.222", None, "DATA_TERBATAS", "1/2", None, ["SUMBER_SIMULASI"]),
]


@pytest.mark.parametrize(("ip", "score", "status", "coverage", "label", "flags"), DEMO)
def test_post_checks_ip_demo(
    client, make_user, login, ip, score, status, coverage, label, flags
):
    make_user("analyst", Role.ANALYST)

    resp = post(client, login, ip)

    assert resp.status_code == 201
    body = resp.json()
    assert body["risk_score"] == score
    assert body["assessment_status"] == status
    assert body["coverage"] == coverage
    assert body["indication"] == label
    assert body["flags"] == flags
    assert body["scoring_version"] == "v1-percobaan"


def test_get_sama_persis_dengan_post_termasuk_flag_dan_pembulatan(
    client, make_user, login
):
    make_user("analyst", Role.ANALYST)
    created = post(client, login, "9.9.9.9").json()

    fetched = client.get(f"{CHECKS}/{created['id']}", headers=login("analyst")).json()
    listed = client.get(CHECKS, headers=login("analyst")).json()["items"][0]

    assert fetched == created
    assert listed == created


def test_db_menyimpan_presisi_penuh_dan_respons_membulatkan_satu_desimal(
    client, make_user, login, db
):
    make_user("analyst", Role.ANALYST)

    body = post(client, login, "1.1.1.1").json()

    db.expire_all()
    stored = db.scalars(select(IpCheck)).one()
    assert stored.risk_score == pytest.approx(4700 / 55)  # 85.454545...
    assert stored.risk_score != 85.5
    assert body["risk_score"] == 85.5


def test_hasil_per_sumber_membawa_field_tahap_1(client, make_user, login):
    make_user("analyst", Role.ANALYST)

    abuse, vt = post(client, login, "1.1.1.1").json()["sources"]

    assert (abuse["source"], abuse["status"], abuse["normalized_score"]) == (
        "abuseipdb",
        "OK_SIGNAL",
        90,
    )
    assert (vt["source"], vt["status"], vt["normalized_score"]) == (
        "virustotal",
        "OK_SIGNAL",
        80,
    )
    assert abuse["evidence_summary"]["simulasi"] is True
    assert abuse["flags"] == vt["flags"] == ["SUMBER_SIMULASI"]
    assert abuse["retrieved_at"].endswith("+07:00")
    assert abuse["from_cache"] is False and abuse["expires_at"] is None
    assert abuse["http_status"] is None  # mock bukan panggilan HTTP


# --- batas label lewat API: dihitung dari nilai tersimpan --------------------------------


@pytest.mark.parametrize(
    ("stored", "shown", "label"),
    [
        (24.99, 25.0, "RENDAH"),
        (25.0, 25.0, "PERLU_PEMERIKSAAN"),
        (49.96, 50.0, "PERLU_PEMERIKSAAN"),
        (50.0, 50.0, "TINGGI"),
        (74.96, 75.0, "TINGGI"),  # tampil 75.0 tetapi label TINGGI
        (75.0, 75.0, "SANGAT_TINGGI"),
    ],
)
def test_label_dari_nilai_tersimpan_bukan_yang_dibulatkan(
    client, make_user, make_check, login, stored, shown, label
):
    make_user("viewer", Role.VIEWER)
    check = make_check(
        "8.8.8.8", "COMPLETE", risk_score=stored, coverage="2/2", flags=[]
    )

    body = client.get(f"{CHECKS}/{check.id}", headers=login("viewer")).json()

    assert body["risk_score"] == shown
    assert body["indication"] == label


# --- data lama tetap terbaca -----------------------------------------------------------------


def test_cek_lama_dengan_sources_tiga_field_tetap_terbaca(
    client, make_user, make_check, login
):
    make_user("viewer", Role.VIEWER)
    old = [
        {
            "source": "abuseipdb",
            "status": "SKIPPED",
            "reason": "ADAPTER_NOT_IMPLEMENTED",
        },
        {
            "source": "virustotal",
            "status": "SKIPPED",
            "reason": "ADAPTER_NOT_IMPLEMENTED",
        },
    ]
    check = make_check("8.8.8.8", sources=old)

    detail = client.get(f"{CHECKS}/{check.id}", headers=login("viewer"))
    listing = client.get(CHECKS, headers=login("viewer"))

    assert detail.status_code == 200 and listing.status_code == 200
    body = detail.json()
    assert body["risk_score"] is None and body["indication"] is None
    assert body["sources"][0] == {
        "source": "abuseipdb",
        "status": "SKIPPED",
        "reason": "ADAPTER_NOT_IMPLEMENTED",
        "normalized_score": None,
        "evidence_summary": {},
        "source_time": None,
        "source_time_type": None,
        "retrieved_at": None,
        "expires_at": None,
        "from_cache": False,
        "http_status": None,
        "duration_ms": None,
        "flags": [],
        "retry_after_seconds": None,
    }


# --- data nyata 29 Okt (adapter asli di atas MockTransport) ---------------------------------


def test_data_nyata_a7_v0_lewat_api_dengan_waktu_wib(
    client, make_user, login, use_sources, db
):
    make_user("analyst", Role.ANALYST)
    use_sources(live_adapters(reply(200, fixture=NYATA_A), reply(200, fixture=NYATA_V)))

    resp = post(client, login, "118.25.6.39")

    assert resp.status_code == 201
    body = resp.json()
    assert body["risk_score"] == 3.8
    assert body["indication"] == "RENDAH"
    assert (body["assessment_status"], body["coverage"]) == ("COMPLETE", "2/2")
    assert body["flags"] == []  # tanpa HASIL_BERBEDA dan tanpa SUMBER_SIMULASI
    abuse, vt = body["sources"]
    assert abuse["source_time"] == "2026-09-18T05:17:21+07:00"  # 22:17:21Z
    assert abuse["source_time_type"] == "last_report"
    assert vt["source_time"] == to_wib_iso(datetime.fromtimestamp(1793236459, UTC))
    assert vt["source_time_type"] == "last_analysis"
    assert abuse["retrieved_at"] == to_wib_iso(NOW)
    assert abuse["http_status"] == 200 and isinstance(abuse["duration_ms"], int)
    # lastReportedAt di bukti tetap apa adanya (UTC); source_time adalah field yang dinormalkan.
    assert abuse["evidence_summary"]["lastReportedAt"] == "2026-09-17T22:17:21+00:00"
    assert "simulasi" not in abuse["evidence_summary"]

    # Penyimpanan: UTC, bukan WIB.
    db.expire_all()
    stored = db.scalars(select(IpCheck)).one().sources[0]
    assert stored["source_time"] == "2026-09-17T22:17:21+00:00"
    assert stored["retrieved_at"] == NOW.isoformat()


# --- sumber gagal: cek tetap tercatat, tidak pernah skor 0 ---------------------------------


def test_semua_sumber_gagal_tetap_201_dengan_alasan_dan_tanpa_skor(
    client, make_user, login, use_sources
):
    make_user("analyst", Role.ANALYST)
    use_sources(
        live_adapters(
            reply(401, raw="bukan json"),
            reply(429, body={}, headers={"Retry-After": "60"}),
        )
    )

    resp = post(client, login, "1.1.1.1")

    assert resp.status_code == 201
    body = resp.json()
    assert body["risk_score"] is None and body["indication"] is None
    assert (body["assessment_status"], body["coverage"]) == ("TIDAK_TERSEDIA", "0/2")
    abuse, vt = body["sources"]
    assert (abuse["status"], abuse["reason"], abuse["http_status"]) == (
        "ERROR",
        "AUTH",
        401,
    )
    assert (vt["status"], vt["reason"], vt["retry_after_seconds"]) == (
        "ERROR",
        "RATE_LIMIT",
        60,
    )
    assert abuse["normalized_score"] is None and vt["normalized_score"] is None


def test_timeout_satu_sumber_menjadi_data_terbatas(
    client, make_user, login, use_sources
):
    make_user("analyst", Role.ANALYST)
    use_sources(live_adapters(reply(200, fixture=NYATA_A), raises(httpx.ReadTimeout)))

    body = post(client, login, "1.1.1.1").json()

    assert (body["assessment_status"], body["coverage"]) == ("DATA_TERBATAS", "1/2")
    assert body["risk_score"] is None
    assert body["sources"][1]["reason"] == "TIMEOUT"


# --- audit: status per sumber, tanpa evidence dan tanpa key ----------------------------------


def test_audit_mencatat_status_per_sumber_tanpa_evidence_atau_key(
    client, make_user, login, use_sources, db
):
    make_user("analyst", Role.ANALYST)
    use_sources(live_adapters(reply(200, fixture=NYATA_A), reply(200, fixture=NYATA_V)))

    post(client, login, "118.25.6.39")

    db.expire_all()
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "ip_check")).one()
    assert set(entry.detail) == {"check_id", "assessment_status", "sources"}
    assert entry.detail["sources"] == {
        "abuseipdb": "OK_SIGNAL",
        "virustotal": "OK_NO_SIGNAL",
    }
    dumped = json.dumps(entry.detail)
    for forbidden in (FAKE_KEY, "evidence", "abuseConfidenceScore", "malicious"):
        assert forbidden not in dumped


def test_key_tidak_muncul_di_respons_maupun_database(
    client, make_user, login, use_sources, db
):
    make_user("analyst", Role.ANALYST)
    use_sources(live_adapters(reply(401, raw="x"), raises(httpx.ConnectError)))

    resp = post(client, login, "1.1.1.1")

    db.expire_all()
    assert FAKE_KEY not in resp.text
    assert FAKE_KEY not in json.dumps(db.scalars(select(IpCheck)).one().sources)
    assert FAKE_KEY not in json.dumps(
        [a.detail for a in db.scalars(select(AuditLog))], default=str
    )


# --- input ditolak tidak menyentuh sumber -------------------------------------------------------


class RecordingSource:
    name = "abuseipdb"

    def __init__(self):
        self.calls: list[str] = []

    def fetch(self, ip):
        self.calls.append(ip)
        raise AssertionError("sumber tidak boleh dipanggil")


@pytest.mark.parametrize("ip", ["10.0.0.5", "127.0.0.1", "abc", "::1"])
def test_input_ditolak_tidak_memanggil_sumber_yang_disuntikkan(
    client, make_user, login, use_sources, ip
):
    make_user("analyst", Role.ANALYST)
    source = RecordingSource()
    use_sources([source])

    resp = post(client, login, ip)

    assert resp.status_code == 422
    assert source.calls == []


def test_viewer_tidak_memanggil_sumber(client, make_user, login, use_sources):
    make_user("viewer", Role.VIEWER)
    source = RecordingSource()
    use_sources([source])

    resp = post(client, login, "8.8.8.8", user="viewer")

    assert resp.status_code == 403
    assert source.calls == []


# --- dokumentasi ------------------------------------------------------------------------------------


def test_openapi_mendokumentasikan_indication_dan_field_sumber(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    check = (
        schemas["CheckOut-Output"]
        if "CheckOut-Output" in schemas
        else schemas["CheckOut"]
    )
    assert "indication" in check["properties"]
    source = schemas["SourceResult"]["properties"]
    assert {
        "normalized_score",
        "evidence_summary",
        "flags",
        "retry_after_seconds",
    } <= set(source)
