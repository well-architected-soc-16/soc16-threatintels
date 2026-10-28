import pytest

from app.core.security import hash_password, verify_password
from scripts.seed_users import SeedConfigError, load_seed_users

VALID_ENV = {
    "SEED_ADMIN_USER": "admin",
    "SEED_ADMIN_PASSWORD": "a" * 12,
    "SEED_ANALYST_MISP_USER": "analyst_misp",
    "SEED_ANALYST_MISP_PASSWORD": "b" * 12,
    "SEED_ANALYST_USER": "analyst",
    "SEED_ANALYST_PASSWORD": "c" * 12,
    "SEED_VIEWER_USER": "viewer",
    "SEED_VIEWER_PASSWORD": "d" * 12,
}


def test_load_seed_users_memetakan_role_dan_izin_misp():
    users = {u.username: u for u in load_seed_users(VALID_ENV)}

    assert users["admin"].role == "admin"
    assert users["analyst_misp"].role == "analyst"
    assert users["analyst_misp"].can_send_misp is True
    assert users["analyst"].can_send_misp is False
    assert users["viewer"].role == "viewer"


def test_password_kurang_dari_12_karakter_ditolak_tanpa_membocorkan_nilai():
    env = {**VALID_ENV, "SEED_VIEWER_PASSWORD": "pendek"}

    with pytest.raises(SeedConfigError) as exc:
        load_seed_users(env)

    assert "SEED_VIEWER_PASSWORD" in str(exc.value)
    assert "pendek" not in str(exc.value)


@pytest.mark.parametrize(
    "var",
    [
        "SEED_ADMIN_PASSWORD",
        "SEED_ANALYST_MISP_PASSWORD",
        "SEED_ANALYST_PASSWORD",
        "SEED_VIEWER_PASSWORD",
    ],
)
@pytest.mark.parametrize(
    "placeholder",
    [
        "ganti-saya-min-12-karakter",
        "GANTI-SAYA-MIN-12-KARAKTER",
        "ganti-RAHASIA-UJI-xx",
    ],
)
def test_password_placeholder_ditolak_tanpa_membocorkan_nilai(var, placeholder):
    env = {**VALID_ENV, var: placeholder}

    with pytest.raises(SeedConfigError) as exc:
        load_seed_users(env)

    assert var in str(exc.value)
    assert "nilai contoh" in str(exc.value)
    assert placeholder not in str(exc.value)
    assert "RAHASIA-UJI" not in str(exc.value)


def test_satu_placeholder_membatalkan_seluruh_seed():
    env = {**VALID_ENV, "SEED_VIEWER_PASSWORD": "ganti-saya-min-12-karakter"}

    with pytest.raises(SeedConfigError) as exc:
        load_seed_users(env)

    assert "SEED_VIEWER_PASSWORD" in str(exc.value)
    assert "SEED_ADMIN_PASSWORD" not in str(exc.value)  # yang valid tidak disebut


def test_semua_nilai_contoh_env_example_ditolak_sekaligus():
    env = {
        k: ("ganti-saya-min-12-karakter" if k.endswith("_PASSWORD") else v)
        for k, v in VALID_ENV.items()
    }

    with pytest.raises(SeedConfigError) as exc:
        load_seed_users(env)

    for var in ("SEED_ADMIN", "SEED_ANALYST_MISP", "SEED_ANALYST", "SEED_VIEWER"):
        assert f"{var}_PASSWORD masih berisi nilai contoh" in str(exc.value)


def test_password_acak_valid_tetap_diterima():
    env = {**VALID_ENV, "SEED_ADMIN_PASSWORD": "3f9a1c7e5b2d4a60"}

    assert {u.username for u in load_seed_users(env)} >= {"admin"}


def test_variabel_kosong_ditolak():
    env = {k: v for k, v in VALID_ENV.items() if k != "SEED_ADMIN_USER"}

    with pytest.raises(SeedConfigError, match="SEED_ADMIN_USER"):
        load_seed_users(env)


def test_username_duplikat_ditolak():
    env = {**VALID_ENV, "SEED_VIEWER_USER": "admin"}

    with pytest.raises(SeedConfigError, match="unik"):
        load_seed_users(env)


def test_hash_password_argon2_dan_bisa_diverifikasi():
    hashed = hash_password("password-uji-12-karakter")

    assert hashed.startswith("$argon2")
    assert verify_password("password-uji-12-karakter", hashed)
    assert not verify_password("salah", hashed)
