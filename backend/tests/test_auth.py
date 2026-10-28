from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.security import ALGORITHM
from app.models import Role, User
from tests.conftest import TEST_PASSWORD

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _token(claims: dict, key: str | None = None) -> str:
    key = key or get_settings().jwt_secret_key.get_secret_value()
    return jwt.encode(claims, key, algorithm=ALGORITHM)


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=5)


def test_login_benar_mengembalikan_token(client, make_user):
    make_user("alice", Role.ANALYST)

    resp = client.post(LOGIN, data={"username": "alice", "password": TEST_PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(
        body["access_token"],
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[ALGORITHM],
    )
    assert claims["sub"] == "alice"
    assert claims["role"] == "analyst"
    assert "exp" in claims


def test_login_password_salah_401(client, make_user):
    make_user("alice")

    resp = client.post(LOGIN, data={"username": "alice", "password": "salah-banget-1"})

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_login_user_tidak_ada_tetap_verifikasi_dummy_hash(client, monkeypatch):
    from app.core.security import DUMMY_HASH
    from app.routers import auth

    calls = []
    real_verify = auth.verify_password

    def spy(password, password_hash):
        calls.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(auth, "verify_password", spy)

    resp = client.post(LOGIN, data={"username": "hantu", "password": "apa-saja-12345"})

    assert resp.status_code == 401
    assert calls == [DUMMY_HASH]


def test_login_pesan_sama_untuk_user_tidak_ada_dan_password_salah(client, make_user):
    make_user("alice")

    wrong_pw = client.post(
        LOGIN, data={"username": "alice", "password": "salah-12345678"}
    )
    no_user = client.post(
        LOGIN, data={"username": "hantu", "password": "salah-12345678"}
    )

    assert wrong_pw.json() == no_user.json()


def test_login_akun_nonaktif_401(client, make_user):
    make_user("alice", is_active=False)

    resp = client.post(LOGIN, data={"username": "alice", "password": TEST_PASSWORD})

    assert resp.status_code == 401


def test_me_mengembalikan_profil_tanpa_hash_dan_waktu_wib(client, make_user, login):
    make_user("alice", Role.ANALYST, can_send_misp=True)

    resp = client.get(ME, headers=login("alice"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "analyst"
    assert body["can_send_misp"] is True
    assert "password_hash" not in body
    assert body["created_at"].endswith("+07:00")


def test_tanpa_token_401(client):
    resp = client.get(ME)

    assert resp.status_code == 401


def test_token_rusak_401(client):
    resp = client.get(ME, headers={"Authorization": "Bearer bukan.jwt.valid"})

    assert resp.status_code == 401


def test_token_kedaluwarsa_401(client, make_user):
    make_user("alice")
    expired = _token(
        {
            "sub": "alice",
            "role": "viewer",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        }
    )

    resp = client.get(ME, headers={"Authorization": f"Bearer {expired}"})

    assert resp.status_code == 401


def test_token_tanda_tangan_salah_401(client, make_user):
    make_user("alice")
    forged = _token(
        {"sub": "alice", "role": "admin", "exp": _future()}, key="kunci-palsu" * 4
    )

    resp = client.get(ME, headers={"Authorization": f"Bearer {forged}"})

    assert resp.status_code == 401


def test_token_tanpa_exp_ditolak(client, make_user):
    make_user("alice")
    no_exp = _token({"sub": "alice", "role": "viewer"})

    resp = client.get(ME, headers={"Authorization": f"Bearer {no_exp}"})

    assert resp.status_code == 401


def test_token_untuk_user_yang_sudah_dihapus_401(client, make_user):
    make_user("alice")
    orphan = _token({"sub": "tidak-ada", "role": "admin", "exp": _future()})

    resp = client.get(ME, headers={"Authorization": f"Bearer {orphan}"})

    assert resp.status_code == 401


def test_token_user_dinonaktifkan_setelah_login_401(client, make_user, login, db):
    make_user("alice")
    headers = login("alice")
    db.query(User).filter_by(username="alice").update({"is_active": False})
    db.commit()

    resp = client.get(ME, headers=headers)

    assert resp.status_code == 401
