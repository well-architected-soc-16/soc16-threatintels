"""Uji RBAC & manajemen user admin. Uji 403 di sini adalah bukti KM-8."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.deps import require_misp_permission
from app.core.security import verify_password
from app.db.session import get_db
from app.models import AuditLog, Role, User
from tests.conftest import TEST_PASSWORD

USERS = "/api/v1/admin/users"


# --- Akses negatif (403) -------------------------------------------------


def test_viewer_get_admin_users_403(client, make_user, login):
    make_user("viewer", Role.VIEWER)

    resp = client.get(USERS, headers=login("viewer"))

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Akses ditolak"}


def test_analyst_patch_admin_users_403(client, make_user, login):
    make_user("analyst", Role.ANALYST)
    target = make_user("viewer", Role.VIEWER)

    resp = client.patch(
        f"{USERS}/{target.id}", json={"role": "admin"}, headers=login("analyst")
    )

    assert resp.status_code == 403


def test_analyst_misp_tetap_tidak_boleh_kelola_user(client, make_user, login):
    make_user("analyst_misp", Role.ANALYST, can_send_misp=True)

    resp = client.post(
        USERS,
        json={"username": "baru", "password": TEST_PASSWORD, "role": "viewer"},
        headers=login("analyst_misp"),
    )

    assert resp.status_code == 403


def test_viewer_tidak_bisa_mengangkat_dirinya_sendiri(client, make_user, login, db):
    viewer = make_user("viewer", Role.VIEWER)

    resp = client.patch(
        f"{USERS}/{viewer.id}", json={"role": "admin"}, headers=login("viewer")
    )

    assert resp.status_code == 403
    db.expire_all()
    assert db.get(User, viewer.id).role == "viewer"


def test_tanpa_token_admin_users_401(client):
    assert client.get(USERS).status_code == 401


def test_role_dibaca_ulang_dari_db_bukan_dari_token(client, make_user, login, db):
    admin = make_user("boss", Role.ADMIN)
    headers = login("boss")  # token memuat role=admin
    db.query(User).filter_by(id=admin.id).update({"role": "viewer"})
    db.commit()

    resp = client.get(USERS, headers=headers)

    assert resp.status_code == 403


# --- Admin ---------------------------------------------------------------


def test_admin_list_users(client, make_user, login):
    make_user("boss", Role.ADMIN)
    make_user("viewer", Role.VIEWER)

    resp = client.get(USERS, headers=login("boss"))

    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["boss", "viewer"]
    assert all("password_hash" not in u for u in resp.json())


def test_admin_beri_can_send_misp_ke_analyst(client, make_user, login):
    make_user("boss", Role.ADMIN)
    analyst = make_user("analyst", Role.ANALYST)

    resp = client.patch(
        f"{USERS}/{analyst.id}", json={"can_send_misp": True}, headers=login("boss")
    )

    assert resp.status_code == 200
    assert resp.json()["can_send_misp"] is True
    assert resp.json()["role"] == "analyst"


def test_admin_cabut_can_send_misp_dan_nonaktifkan_user(client, make_user, login):
    make_user("boss", Role.ADMIN)
    analyst = make_user("analyst", Role.ANALYST, can_send_misp=True)

    resp = client.patch(
        f"{USERS}/{analyst.id}",
        json={"can_send_misp": False, "is_active": False},
        headers=login("boss"),
    )

    assert resp.status_code == 200
    assert resp.json()["can_send_misp"] is False
    assert resp.json()["is_active"] is False


def test_admin_buat_user_baru_hash_argon2_dan_bisa_login(client, make_user, login, db):
    make_user("boss", Role.ADMIN)

    resp = client.post(
        USERS,
        json={"username": "baru", "password": "password-baru-12345", "role": "analyst"},
        headers=login("boss"),
    )

    assert resp.status_code == 201
    assert "password" not in resp.json()
    assert "password_hash" not in resp.json()
    stored = db.scalar(select(User).where(User.username == "baru"))
    assert stored.password_hash.startswith("$argon2")
    assert verify_password("password-baru-12345", stored.password_hash)
    login("baru", "password-baru-12345")


def test_admin_buat_user_username_duplikat_409(client, make_user, login):
    make_user("boss", Role.ADMIN)
    make_user("viewer", Role.VIEWER)

    resp = client.post(
        USERS,
        json={"username": "viewer", "password": TEST_PASSWORD, "role": "viewer"},
        headers=login("boss"),
    )

    assert resp.status_code == 409


def test_admin_buat_user_password_pendek_422(client, make_user, login):
    make_user("boss", Role.ADMIN)

    resp = client.post(
        USERS,
        json={"username": "baru", "password": "pendek", "role": "viewer"},
        headers=login("boss"),
    )

    assert resp.status_code == 422


def test_admin_buat_user_role_tidak_dikenal_422(client, make_user, login):
    make_user("boss", Role.ADMIN)

    resp = client.post(
        USERS,
        json={"username": "baru", "password": TEST_PASSWORD, "role": "superuser"},
        headers=login("boss"),
    )

    assert resp.status_code == 422


def test_admin_patch_user_tidak_ada_404(client, make_user, login):
    make_user("boss", Role.ADMIN)

    resp = client.patch(
        f"{USERS}/9999", json={"is_active": False}, headers=login("boss")
    )

    assert resp.status_code == 404


def test_admin_tidak_boleh_menurunkan_atau_menonaktifkan_diri_sendiri(
    client, make_user, login
):
    boss = make_user("boss", Role.ADMIN)
    headers = login("boss")

    demote = client.patch(
        f"{USERS}/{boss.id}", json={"role": "viewer"}, headers=headers
    )
    deactivate = client.patch(
        f"{USERS}/{boss.id}", json={"is_active": False}, headers=headers
    )

    assert demote.status_code == 409
    assert deactivate.status_code == 409


# --- require_misp_permission (dipakai endpoint IoC di Tahap 4) -----------


def _misp_app(client: TestClient) -> TestClient:
    mini = FastAPI()
    mini.dependency_overrides = {get_db: client.app.dependency_overrides[get_db]}

    @mini.post("/kirim", dependencies=[Depends(require_misp_permission)])
    def kirim() -> dict:
        return {"ok": True}

    return TestClient(mini)


def test_require_misp_permission(client, make_user, login):
    make_user("boss", Role.ADMIN)
    make_user("analyst_misp", Role.ANALYST, can_send_misp=True)
    make_user("analyst", Role.ANALYST)
    make_user("viewer_flag", Role.VIEWER, can_send_misp=True)
    tokens = {n: login(n) for n in ("boss", "analyst_misp", "analyst", "viewer_flag")}
    mini = _misp_app(client)

    assert mini.post("/kirim", headers=tokens["boss"]).status_code == 200
    assert mini.post("/kirim", headers=tokens["analyst_misp"]).status_code == 200
    assert mini.post("/kirim", headers=tokens["analyst"]).status_code == 403
    assert mini.post("/kirim", headers=tokens["viewer_flag"]).status_code == 403


# --- Audit log -----------------------------------------------------------


def _audit(db) -> list[AuditLog]:
    db.expire_all()
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))


def test_akses_403_tercatat_di_audit_log(client, make_user, login, db):
    make_user("viewer", Role.VIEWER)
    headers = login("viewer")

    client.get(USERS, headers=headers)

    denied = [a for a in _audit(db) if a.action == "access_denied"]
    assert len(denied) == 1
    assert denied[0].result == "denied"
    assert denied[0].actor_username == "viewer"
    assert denied[0].target == f"GET {USERS}"
    assert denied[0].detail == {"required_roles": ["admin"]}


def test_login_sukses_dan_gagal_tercatat(client, make_user, db):
    make_user("alice")

    client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": TEST_PASSWORD}
    )
    client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": "salah-12345678"}
    )
    client.post(
        "/api/v1/auth/login", data={"username": "hantu", "password": "salah-12345678"}
    )

    logs = _audit(db)
    assert [(a.action, a.result, a.actor_username) for a in logs] == [
        ("login", "success", "alice"),
        ("login", "denied", None),
        ("login", "denied", None),
    ]
    assert logs[1].detail == {"username": "alice", "reason": "password_salah"}
    assert logs[2].detail == {"username": "hantu", "reason": "user_tidak_ada"}


def test_perubahan_user_tercatat_dengan_diff(client, make_user, login, db):
    make_user("boss", Role.ADMIN)
    analyst = make_user("analyst", Role.ANALYST)
    headers = login("boss")

    client.post(
        USERS,
        json={"username": "baru", "password": "password-baru-12345", "role": "viewer"},
        headers=headers,
    )
    client.patch(f"{USERS}/{analyst.id}", json={"can_send_misp": True}, headers=headers)

    by_action = {a.action: a for a in _audit(db) if a.action.startswith("user_")}
    assert by_action["user_create"].target == "baru"
    assert by_action["user_create"].actor_username == "boss"
    assert by_action["user_update"].target == "analyst"
    assert by_action["user_update"].detail == {
        "changes": {"can_send_misp": [False, True]}
    }


def test_audit_log_tidak_memuat_password_atau_token(client, make_user, login, db):
    make_user("boss", Role.ADMIN)
    make_user("viewer", Role.VIEWER)
    admin_headers = login("boss")
    viewer_headers = login("viewer")
    client.post(
        USERS,
        json={"username": "baru", "password": "rahasia-banget-123", "role": "viewer"},
        headers=admin_headers,
    )
    client.get(USERS, headers=viewer_headers)  # 403
    client.post(
        "/api/v1/auth/login", data={"username": "boss", "password": "rahasia-salah-999"}
    )

    dump = " ".join(
        f"{a.actor_username} {a.action} {a.target} {a.detail} {a.ip_address}"
        for a in _audit(db)
    )
    for secret in (
        TEST_PASSWORD,
        "rahasia-banget-123",
        "rahasia-salah-999",
        admin_headers["Authorization"].split()[1],
        viewer_headers["Authorization"].split()[1],
        "$argon2",
    ):
        assert secret not in dump
