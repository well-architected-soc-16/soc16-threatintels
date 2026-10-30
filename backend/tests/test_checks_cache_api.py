"""Cache dan kuota lewat `POST /checks` (TASK-02 Tahap 3), termasuk bahwa input yang ditolak dan
viewer tidak pernah menyentuh cache, pembatas kuota, maupun jaringan.

Mode mock (default test) memakai `get_sources` asli; mode live memakai adapter asli di atas
`MockTransport`, dibungkus `SourceGateway` asli di atas database test.
"""

import pytest
from sqlalchemy import func, select

from app.main import app
from app.models import AuditLog, IocSubmission, Role, SourceCache, SourceCall
from app.services.misp import SubmissionResult, get_misp_client
from app.services.sources import cache, quota
from app.services.sources.factory import get_sources
from tests.sources_support import (
    NYATA_ABUSEIPDB,
    NYATA_VIRUSTOTAL,
    live_adapters_with_requests,
    make_gateway,
    post,
    reply,
)

CHECKS = "/api/v1/checks"
MISP = "/api/v1/iocs/misp"
REJECTED = [
    "10.0.0.5",
    "127.0.0.1",
    "192.168.1.1",
    "169.254.1.1",
    "224.0.0.1",
    "192.0.2.1",
    "abc",
    "::1",
]


@pytest.fixture
def use_live(engine):
    """Pasang gerbang live (adapter asli + MockTransport) sebagai `get_sources`."""

    def _use():
        adapters, abuse_seen, vt_seen = live_adapters_with_requests(
            reply(200, fixture=NYATA_ABUSEIPDB), reply(200, fixture=NYATA_VIRUSTOTAL)
        )
        app.dependency_overrides[get_sources] = lambda: [
            make_gateway(a, engine, mode="live") for a in adapters
        ]
        return abuse_seen, vt_seen

    yield _use
    app.dependency_overrides.pop(get_sources, None)


def count(db, model) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model)) or 0


# --- cache lewat API ---------------------------------------------------------------------------------


def test_ip_sama_dua_kali_hasil_kedua_dari_cache_dengan_retrieved_at_asli(
    client, make_user, login, use_live
):
    make_user("analyst", Role.ANALYST)
    abuse_seen, vt_seen = use_live()

    first = post(client, login, "118.25.6.39").json()
    second = post(client, login, "118.25.6.39").json()

    assert [s["from_cache"] for s in first["sources"]] == [False, False]
    assert [s["from_cache"] for s in second["sources"]] == [True, True]
    for a, b in zip(first["sources"], second["sources"], strict=True):
        assert b["retrieved_at"] == a["retrieved_at"]  # waktu pengambilan asli
        assert b["expires_at"] == a["expires_at"] and b["expires_at"] is not None
        assert b["http_status"] is None  # tak ada request baru pada pembacaan cache
    assert (len(abuse_seen), len(vt_seen)) == (1, 1)  # adapter tidak dipanggil lagi
    assert (second["risk_score"], second["indication"]) == (3.8, "RENDAH")


def test_cek_ke_5_vt_skipped_quota_internal_abuseipdb_jalan_data_terbatas(
    client, make_user, login, use_live, db
):
    make_user("analyst", Role.ANALYST)
    abuse_seen, vt_seen = use_live()

    bodies = [
        post(client, login, ip).json()
        for ip in ("8.8.8.8", "1.1.1.1", "9.9.9.9", "4.4.4.4", "5.5.5.5")
    ]

    assert [b["assessment_status"] for b in bodies[:4]] == ["COMPLETE"] * 4
    fifth = bodies[4]
    abuse, vt = fifth["sources"]
    assert (abuse["status"], vt["status"], vt["reason"]) == (
        "OK_SIGNAL",
        "SKIPPED",
        "QUOTA_INTERNAL",
    )
    assert (fifth["assessment_status"], fifth["coverage"]) == ("DATA_TERBATAS", "1/2")
    assert fifth["risk_score"] is None and fifth["indication"] is None
    assert (len(abuse_seen), len(vt_seen)) == (
        5,
        4,
    )  # tak ada request keluar saat SKIPPED
    db.expire_all()
    audit = db.scalars(
        select(AuditLog).where(AuditLog.action == "ip_check").order_by(AuditLog.id)
    ).all()
    assert audit[4].detail["sources"] == {
        "abuseipdb": "OK_SIGNAL",
        "virustotal": "SKIPPED",
    }


# --- mode mock: cache tidak boleh melepas flag simulasi -----------------------------------------------


class SpyMisp:
    def __init__(self):
        self.calls = 0

    def submit_indicator(self, ip, reason, tags, submitted_by):
        self.calls += 1
        return SubmissionResult(status="mock_sent", misp_event_uuid="MOCK-spy")


def test_hasil_mock_dari_cache_tetap_berflag_simulasi_dan_ditolak_misp(
    client, make_user, login, db
):
    make_user("misp", Role.ANALYST, can_send_misp=True)
    spy = SpyMisp()
    app.dependency_overrides[get_misp_client] = lambda: spy
    try:
        first = post(client, login, "1.1.1.1", user="misp").json()
        second = post(client, login, "1.1.1.1", user="misp").json()
        resp = client.post(
            MISP,
            json={"check_id": second["id"], "reason": "Uji guard simulasi dari cache"},
            headers=login("misp"),
        )
    finally:
        app.dependency_overrides.pop(get_misp_client, None)

    assert [s["from_cache"] for s in first["sources"]] == [False, False]
    assert [s["from_cache"] for s in second["sources"]] == [True, True]
    assert first["flags"] == second["flags"] == ["SUMBER_SIMULASI"]
    assert second["risk_score"] == first["risk_score"] == 85.5
    assert second["sources"][0]["evidence_summary"]["simulasi"] is True
    assert resp.status_code == 422 and "SUMBER_SIMULASI" in resp.json()["detail"]
    assert spy.calls == 0 and count(db, IocSubmission) == 0


def test_hasil_vt_all_undetected_dari_cache_tetap_berflag_no_vendor_opinion(
    client, make_user, login
):
    make_user("analyst", Role.ANALYST)

    first = post(client, login, "149.112.112.112").json()
    second = post(client, login, "149.112.112.112").json()

    assert second["sources"][1]["from_cache"] is True
    assert first["flags"] == second["flags"] == ["NO_VENDOR_OPINION", "SUMBER_SIMULASI"]


def test_mode_mock_banyak_cek_tidak_pernah_skipped_dan_dicatat_sebagai_mock(
    client, make_user, login, db
):
    make_user("analyst", Role.ANALYST)
    ips = [f"30.0.0.{n}" for n in range(1, 11)]

    bodies = [post(client, login, ip).json() for ip in ips]

    assert all(s["status"] != "SKIPPED" for b in bodies for s in b["sources"])
    db.expire_all()
    modes = set(db.scalars(select(SourceCall.mode)))
    assert modes == {"mock"}
    assert set(db.scalars(select(SourceCache.mode))) == {"mock"}


# --- input ditolak dan viewer tidak menyentuh cache, kuota, maupun jaringan -----------------------------------


@pytest.fixture
def spies(monkeypatch):
    """Rekam setiap akses cache (baca/tulis) dan kuota (reservasi/selesai); semuanya tetap berjalan."""
    seen: list[str] = []
    for module, name in (
        (cache, "lookup"),
        (cache, "store"),
        (quota, "reserve"),
        (quota, "finalize"),
    ):
        real = getattr(module, name)

        def wrapper(*args, _real=real, _label=f"{module.__name__}.{name}", **kwargs):
            seen.append(_label)
            return _real(*args, **kwargs)

        monkeypatch.setattr(module, name, wrapper)
    return seen


@pytest.mark.parametrize("ip", REJECTED)
def test_input_ditolak_nol_akses_cache_nol_kuota(
    client, make_user, login, db, spies, ip
):
    make_user("analyst", Role.ANALYST)

    resp = post(client, login, ip)

    assert resp.status_code == 422
    assert spies == []  # nol baca cache, nol tulis cache, nol hitung kuota
    assert count(db, SourceCache) == 0 and count(db, SourceCall) == 0


def test_viewer_403_nol_akses_cache_nol_kuota(client, make_user, login, db, spies):
    make_user("viewer", Role.VIEWER)

    resp = post(client, login, "8.8.8.8", user="viewer")

    assert resp.status_code == 403
    assert spies == []
    assert count(db, SourceCache) == 0 and count(db, SourceCall) == 0


def test_tanpa_token_401_nol_akses_cache_nol_kuota(client, db, spies):
    resp = client.post(CHECKS, json={"ip": "8.8.8.8"})

    assert resp.status_code == 401
    assert spies == []


def test_membangun_get_sources_tidak_menyentuh_cache_atau_kuota(db, spies):
    sources = get_sources(db)

    assert [s.name for s in sources] == ["abuseipdb", "virustotal"]
    assert spies == []
    assert count(db, SourceCache) == 0 and count(db, SourceCall) == 0


def test_kontrol_spy_mendeteksi_akses_pada_ip_valid(client, make_user, login, spies):
    make_user("analyst", Role.ANALYST)

    assert post(client, login, "8.8.8.8").status_code == 201

    # Tanpa kontrol ini, test "nol akses" di atas bisa lulus karena spy yang rusak.
    assert "app.services.sources.cache.lookup" in spies
    assert "app.services.sources.quota.reserve" in spies
    assert "app.services.sources.cache.store" in spies
