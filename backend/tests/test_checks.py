import socket

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, IpCheck, Role
from app.routers import checks as checks_router

CHECKS = "/api/v1/checks"

REJECTED_INPUTS = [
    ("10.0.0.5", "PRIVATE"),
    ("127.0.0.1", "LOOPBACK"),
    ("192.168.1.1", "PRIVATE"),
    ("169.254.1.1", "LINK_LOCAL"),
    ("224.0.0.1", "MULTICAST"),
    ("192.0.2.1", "DOCUMENTATION"),
    ("abc", "INVALID_FORMAT"),
    ("::1", "IPV6_NOT_SUPPORTED"),
]


def _count(db, model) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model))


# --- POST /checks: input valid ------------------------------------------


def test_ip_publik_disimpan_sebagai_placeholder_jujur(client, make_user, login):
    make_user("analyst", Role.ANALYST)

    resp = client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=login("analyst"))

    assert resp.status_code == 201
    body = resp.json()
    assert body["ip"] == "8.8.8.8"
    assert body["assessment_status"] == "TIDAK_TERSEDIA"
    assert body["coverage"] == "0/2"
    assert body["risk_score"] is None  # bukan 0
    assert body["scoring_version"] == "v1-percobaan"
    assert body["flags"] == []
    assert body["checked_by"] == "analyst"
    assert body["checked_at"].endswith("+07:00")
    assert body["sources"] == [
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


def test_admin_juga_boleh_membuat_cek(client, make_user, login):
    make_user("boss", Role.ADMIN)

    resp = client.post(CHECKS, json={"ip": "1.1.1.1"}, headers=login("boss"))

    assert resp.status_code == 201


def test_ip_dengan_spasi_disimpan_dalam_bentuk_bersih(client, make_user, login):
    make_user("analyst", Role.ANALYST)

    resp = client.post(CHECKS, json={"ip": " 8.8.8.8 "}, headers=login("analyst"))

    assert resp.status_code == 201
    assert resp.json()["ip"] == "8.8.8.8"


def test_cek_valid_tercatat_di_audit(client, make_user, login, db):
    make_user("analyst", Role.ANALYST)

    client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=login("analyst"))

    db.expire_all()
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "ip_check")).one()
    assert (entry.result, entry.actor_username, entry.target) == (
        "success",
        "analyst",
        "8.8.8.8",
    )
    assert entry.detail["assessment_status"] == "TIDAK_TERSEDIA"


# --- POST /checks: input ditolak ----------------------------------------


@pytest.mark.parametrize(("ip", "reason"), REJECTED_INPUTS)
def test_input_ditolak_422_dengan_reason_tepat(
    client, make_user, login, db, ip, reason
):
    make_user("analyst", Role.ANALYST)

    resp = client.post(CHECKS, json={"ip": ip}, headers=login("analyst"))

    assert resp.status_code == 422
    body = resp.json()
    assert body["assessment_status"] == "INPUT_DITOLAK"
    assert body["risk_score"] is None
    assert body["reason_code"] == reason
    assert body["message"]
    assert _count(db, IpCheck) == 0  # tidak disimpan sebagai cek


def test_input_ditolak_tercatat_di_audit(client, make_user, login, db):
    make_user("analyst", Role.ANALYST)

    client.post(CHECKS, json={"ip": "10.0.0.5"}, headers=login("analyst"))

    db.expire_all()
    entry = db.scalars(
        select(AuditLog).where(AuditLog.action == "ip_check_rejected")
    ).one()
    assert (entry.result, entry.actor_username, entry.target) == (
        "denied",
        "analyst",
        "10.0.0.5",
    )
    assert entry.detail == {"reason_code": "PRIVATE"}


def test_input_ditolak_tidak_memicu_adapter_maupun_koneksi_keluar(
    client, make_user, login, monkeypatch
):
    make_user("analyst", Role.ANALYST)
    headers = login("analyst")  # login (DB) dilakukan sebelum jaringan diblokir
    adapter_calls = []

    def fail_network(*args, **kwargs):
        raise AssertionError("request keluar tidak boleh terjadi untuk input ditolak")

    monkeypatch.setattr(
        checks_router.ip_checks,
        "collect_sources",
        lambda ip: adapter_calls.append(ip) or [],
    )
    monkeypatch.setattr(socket.socket, "connect", fail_network)
    monkeypatch.setattr(socket, "getaddrinfo", fail_network)

    for ip, _ in REJECTED_INPUTS:
        resp = client.post(CHECKS, json={"ip": ip}, headers=headers)
        assert resp.status_code == 422

    assert adapter_calls == []


def test_ip_valid_memanggil_adapter_tepat_sekali(client, make_user, login, monkeypatch):
    make_user("analyst", Role.ANALYST)
    headers = login("analyst")
    adapter_calls = []

    def spy(ip):
        adapter_calls.append(ip)
        return []

    monkeypatch.setattr(checks_router.ip_checks, "collect_sources", spy)

    client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=headers)

    assert adapter_calls == ["8.8.8.8"]


def test_body_tanpa_ip_422_standar(client, make_user, login):
    make_user("analyst", Role.ANALYST)

    resp = client.post(CHECKS, json={}, headers=login("analyst"))

    assert resp.status_code == 422
    assert "detail" in resp.json()


# --- RBAC ----------------------------------------------------------------


def test_viewer_post_checks_403(client, make_user, login, db):
    make_user("viewer", Role.VIEWER)

    resp = client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=login("viewer"))

    assert resp.status_code == 403
    assert _count(db, IpCheck) == 0


def test_viewer_ditolak_tanpa_memvalidasi_atau_memanggil_adapter(
    client, make_user, login, monkeypatch
):
    make_user("viewer", Role.VIEWER)
    headers = login("viewer")
    adapter_calls = []
    monkeypatch.setattr(
        checks_router.ip_checks,
        "collect_sources",
        lambda ip: adapter_calls.append(ip) or [],
    )

    resp = client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=headers)

    assert resp.status_code == 403
    assert adapter_calls == []


def test_tanpa_token_401(client):
    assert client.post(CHECKS, json={"ip": "8.8.8.8"}).status_code == 401
    assert client.get(CHECKS).status_code == 401
    assert client.get(f"{CHECKS}/1").status_code == 401


# --- GET /checks ---------------------------------------------------------


def test_semua_role_boleh_melihat_history(client, make_user, login):
    make_user("analyst", Role.ANALYST)
    make_user("viewer", Role.VIEWER)
    make_user("boss", Role.ADMIN)
    client.post(CHECKS, json={"ip": "8.8.8.8"}, headers=login("analyst"))

    for name in ("analyst", "viewer", "boss"):
        resp = client.get(CHECKS, headers=login(name))
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


def test_paginasi_terbaru_dulu(client, make_user, login):
    make_user("analyst", Role.ANALYST)
    headers = login("analyst")
    for ip in ("8.8.8.8", "1.1.1.1", "9.9.9.9"):
        client.post(CHECKS, json={"ip": ip}, headers=headers)

    page1 = client.get(CHECKS, params={"limit": 2}, headers=headers).json()
    page2 = client.get(CHECKS, params={"limit": 2, "offset": 2}, headers=headers).json()

    assert page1["total"] == 3
    assert [c["ip"] for c in page1["items"]] == ["9.9.9.9", "1.1.1.1"]
    assert [c["ip"] for c in page2["items"]] == ["8.8.8.8"]
    assert (page1["limit"], page1["offset"]) == (2, 0)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_paginasi_parameter_tidak_valid_422(client, make_user, login, params):
    make_user("viewer", Role.VIEWER)

    resp = client.get(CHECKS, params=params, headers=login("viewer"))

    assert resp.status_code == 422


def test_get_check_by_id(client, make_user, login):
    make_user("analyst", Role.ANALYST)
    make_user("viewer", Role.VIEWER)
    created = client.post(
        CHECKS, json={"ip": "8.8.8.8"}, headers=login("analyst")
    ).json()

    resp = client.get(f"{CHECKS}/{created['id']}", headers=login("viewer"))

    assert resp.status_code == 200
    assert resp.json() == created


def test_get_check_tidak_ada_404(client, make_user, login):
    make_user("viewer", Role.VIEWER)

    resp = client.get(f"{CHECKS}/9999", headers=login("viewer"))

    assert resp.status_code == 404
