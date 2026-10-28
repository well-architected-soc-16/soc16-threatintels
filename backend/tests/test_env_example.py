"""Penjaga drift: nilai contoh di `.env.example` HARUS ditolak oleh aplikasi dan seed.

Satu-satunya tempat `.env.example` dibaca. Kode aplikasi mendeteksi placeholder lewat
awalan `ganti-`, bukan lewat file ini, jadi test inilah yang memastikan isi file contoh
tidak diam-diam berubah menjadi nilai yang lolos validasi.

Di container, file ini tersedia lewat bind mount read-only di `docker-compose.yml`
(service `api`, khusus dev). Test GAGAL (bukan skip) jika file tidak ditemukan.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from pydantic import ValidationError

from app.core.config import Settings
from scripts.seed_users import SeedConfigError, load_seed_users

BACKEND_DIR = Path(__file__).resolve().parents[1]
# Repo: root repo (di sebelah backend/). Container: /app/.env.example (bind mount).
CANDIDATES = [BACKEND_DIR.parent / ".env.example", BACKEND_DIR / ".env.example"]


@pytest.fixture(scope="module")
def example_env() -> dict[str, str]:
    for path in CANDIDATES:
        if path.is_file():
            values = {k: v for k, v in dotenv_values(path).items() if v is not None}
            assert values, f"{path} kosong atau tidak terbaca"
            return values
    pytest.fail(
        ".env.example tidak ditemukan; dicari di: "
        + ", ".join(str(p) for p in CANDIDATES)
        + ". Test ini sengaja tidak di-skip. Di container, pastikan service `api` di "
        "docker-compose.yml me-mount './.env.example:/app/.env.example:ro' "
        "(lalu `docker compose up -d --force-recreate api`)."
    )


def _start(env: dict[str, str]) -> subprocess.CompletedProcess:
    # Hanya nilai dari .env.example (+ PATH), tanpa warisan environment container.
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        check=False,
        cwd=BACKEND_DIR,
        env={"PATH": os.environ["PATH"], **env},
        capture_output=True,
        text=True,
        timeout=90,
    )


def test_jwt_contoh_ditolak_settings(example_env):
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            jwt_secret_key=example_env["JWT_SECRET_KEY"],
            db_name="x",
            db_user="x",
            db_password_file=Path("/tidak/dibaca"),
        )


def test_semua_password_seed_contoh_ditolak(example_env):
    password_vars = [
        k for k in example_env if k.startswith("SEED_") and k.endswith("_PASSWORD")
    ]
    assert len(password_vars) == 4

    with pytest.raises(SeedConfigError) as exc:
        load_seed_users(example_env)

    for var in password_vars:
        assert f"{var} masih berisi nilai contoh" in str(exc.value)
        assert example_env[var] not in str(exc.value)


def test_start_dengan_env_example_apa_adanya_gagal_tanpa_membocorkan_nilai(
    example_env,
):
    proc = _start(example_env)

    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "JWT_SECRET_KEY" in out
    assert example_env["JWT_SECRET_KEY"] not in out


def test_start_dengan_env_example_dan_jwt_acak_valid_normal(example_env):
    proc = _start({**example_env, "JWT_SECRET_KEY": secrets.token_hex(32)})

    assert proc.returncode == 0, proc.stdout + proc.stderr
