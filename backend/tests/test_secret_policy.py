"""Aplikasi dan seed menolak nilai secret contoh/lemah (issue #17).

Tidak ada test di sini yang membaca `.env.example`; nilai contoh ditulis ulang secara
harfiah. Deteksi di kode memakai awalan `ganti-`, bukan isi `.env.example`.
"""

import os
import subprocess
import sys
import traceback
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.secret_policy import is_placeholder

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Nilai contoh seperti tertulis di .env.example (ditulis ulang; sengaja tidak dibaca dari file).
EXAMPLE_JWT = "ganti-dengan-string-acak-minimal-32-karakter"
VALID_JWT = "k" * 32
# Nilai uji yang mudah dicari di teks error/log jika bocor.
LEAKY_SHORT = "RAHASIA-UJI-PENDEK"
LEAKY_PLACEHOLDER = "ganti-RAHASIA-UJI-" + "z" * 40


def _settings(jwt_secret_key: str) -> Settings:
    return Settings(
        jwt_secret_key=jwt_secret_key,
        db_name="x",
        db_user="x",
        db_password_file=Path("/tidak/dibaca"),
    )


# --- is_placeholder ------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        EXAMPLE_JWT,
        "ganti-saya-min-12-karakter",
        "GANTI-saya",
        "Ganti-Saya",
        "  ganti-x",
        "ganti-",
    ],
)
def test_nilai_berawalan_ganti_dikenali_sebagai_placeholder(value):
    assert is_placeholder(value) is True


@pytest.mark.parametrize(
    "value", ["", "gantiX", "ganti", "xganti-", "3f9a" * 8, "kata-sandi-biasa"]
)
def test_nilai_lain_bukan_placeholder(value):
    assert is_placeholder(value) is False


# --- JWT_SECRET_KEY di Settings ------------------------------------------


@pytest.mark.parametrize(
    "value",
    [EXAMPLE_JWT, EXAMPLE_JWT.upper(), "Ganti-" + "x" * 40, "  ganti-" + "x" * 40],
)
def test_jwt_placeholder_ditolak_walau_panjangnya_cukup(value):
    assert len(value.encode()) >= 32

    with pytest.raises(ValidationError, match="nilai contoh"):
        _settings(value)


@pytest.mark.parametrize("value", ["", "a", "a" * 31, "é" * 15])
def test_jwt_kurang_dari_32_byte_ditolak(value):
    with pytest.raises(ValidationError, match="kurang dari 32 byte"):
        _settings(value)


@pytest.mark.parametrize("value", ["a" * 32, "a" * 64, "é" * 16, "ab" * 40])
def test_jwt_32_byte_atau_lebih_diterima(value):
    assert _settings(value).jwt_secret_key.get_secret_value() == value


def test_batas_dihitung_dalam_byte_bukan_karakter():
    # 15 karakter "é" = 30 byte (ditolak); 16 karakter = 32 byte (diterima).
    with pytest.raises(ValidationError):
        _settings("é" * 15)
    assert _settings("é" * 16)


def test_pesan_error_menyebut_variabel_dan_cara_memperbaiki():
    with pytest.raises(ValidationError) as exc:
        _settings(EXAMPLE_JWT)

    text = str(exc.value)
    assert "JWT_SECRET_KEY" in text
    assert "openssl rand -hex 32" in text


@pytest.mark.parametrize("secret", [LEAKY_SHORT, LEAKY_PLACEHOLDER])
def test_nilai_secret_tidak_muncul_di_teks_error(secret):
    with pytest.raises(ValidationError) as exc:
        _settings(secret)

    rendered = "\n".join(
        [
            str(exc.value),
            repr(exc.value),
            "".join(traceback.format_exception(exc.value)),
        ]
    )
    assert secret not in rendered
    assert "RAHASIA-UJI" not in rendered


def test_hide_input_in_errors_aktif():
    assert Settings.model_config["hide_input_in_errors"] is True


# --- Start nyata: import app.main dan langkah pertama entrypoint ---------


def _run(args: list[str], jwt_secret_key: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "JWT_SECRET_KEY": jwt_secret_key}
    return subprocess.run(
        [sys.executable, *args],
        check=False,  # returncode diperiksa sendiri oleh tiap test
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )


def _output(proc: subprocess.CompletedProcess) -> str:
    return proc.stdout + proc.stderr


@pytest.mark.parametrize("secret", [LEAKY_SHORT, LEAKY_PLACEHOLDER, EXAMPLE_JWT])
def test_aplikasi_gagal_start_dengan_secret_lemah_tanpa_membocorkan_nilai(secret):
    proc = _run(["-c", "import app.main"], secret)

    out = _output(proc)
    assert proc.returncode != 0
    assert "JWT_SECRET_KEY" in out
    assert "RAHASIA-UJI" not in out
    assert "aplikasi dimulai" not in out  # tidak sampai ke log startup


@pytest.mark.parametrize("secret", [LEAKY_SHORT, LEAKY_PLACEHOLDER])
def test_migrasi_langkah_pertama_entrypoint_juga_gagal_tanpa_bocor(secret):
    # entrypoint.sh menjalankan `alembic upgrade head` lebih dulu, dengan `set -e`.
    proc = _run(["-m", "alembic", "current"], secret)

    out = _output(proc)
    assert proc.returncode != 0
    assert "JWT_SECRET_KEY" in out
    assert "RAHASIA-UJI" not in out


def test_start_dengan_secret_acak_valid_normal_dan_tidak_dilog():
    secret = "q7Zx" * 16  # 64 byte
    proc = _run(["-c", "import app.main"], secret)

    out = _output(proc)
    assert proc.returncode == 0, out
    assert "aplikasi dimulai" in out
    assert secret not in out
