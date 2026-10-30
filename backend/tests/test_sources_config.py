"""Konfigurasi sumber reputasi (TASK-02 Tahap 0 dan 3): default, rentang, file API key, mode live.

- `load_api_key`: validasi file key, dites langsung tanpa lewat `SOURCES_MODE`;
- mode live: file key hilang/kosong/placeholder gagal start dan hanya menyebut nama variabel;
  file key valid diterima. Guard "belum didukung" (Tahap 0) dicabut di Tahap 3.
"""

import os
import subprocess
import sys
import traceback
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.core.secret_policy import SecretFileError, load_api_key

BACKEND_DIR = Path(__file__).resolve().parents[1]

VALID_JWT = "k" * 32
# Nilai uji yang mudah dicari di teks error/log jika bocor.
LEAKY_KEY = "KEY-UJI-RAHASIA-0123456789abcdef"
ABUSE_VAR = "ABUSEIPDB_API_KEY_FILE"
VT_VAR = "VIRUSTOTAL_API_KEY_FILE"


def _key_file(tmp_path: Path, name: str, content: str | bytes) -> Path:
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _settings(**overrides) -> Settings:
    values = {
        "jwt_secret_key": VALID_JWT,
        "db_name": "x",
        "db_user": "x",
        "db_password_file": Path("/tidak/dibaca"),
        **overrides,
    }
    return Settings(**values)


def _rendered(exc_info) -> str:
    return "\n".join(
        [
            str(exc_info.value),
            repr(exc_info.value),
            "".join(traceback.format_exception(exc_info.value)),
        ]
    )


# --- Default dan rentang --------------------------------------------------


def test_default_sumber_sesuai_rencana():
    s = _settings()

    assert s.sources_mode == "mock"
    assert s.abuseipdb_api_key_file == Path("/run/secrets/abuseipdb_api_key")
    assert s.virustotal_api_key_file == Path("/run/secrets/virustotal_api_key")
    assert s.source_timeout_seconds == 10
    assert s.abuseipdb_max_age_days == 30
    assert s.abuseipdb_daily_limit == 1000
    assert s.vt_daily_limit == 500
    assert s.vt_per_minute_limit == 4
    assert s.cache_ttl_ok_signal_hours == 6
    assert s.cache_ttl_ok_no_signal_hours == 24
    assert s.cache_ttl_no_record_hours == 1


@pytest.mark.parametrize("days", [1, 30, 365])
def test_max_age_days_dalam_rentang_diterima(days):
    assert _settings(abuseipdb_max_age_days=days).abuseipdb_max_age_days == days


@pytest.mark.parametrize("days", [0, -1, 366])
def test_max_age_days_di_luar_rentang_ditolak(days):
    with pytest.raises(ValidationError, match="abuseipdb_max_age_days"):
        _settings(abuseipdb_max_age_days=days)


@pytest.mark.parametrize(
    "field",
    [
        "source_timeout_seconds",
        "abuseipdb_daily_limit",
        "vt_daily_limit",
        "vt_per_minute_limit",
        "cache_ttl_ok_signal_hours",
        "cache_ttl_ok_no_signal_hours",
        "cache_ttl_no_record_hours",
    ],
)
@pytest.mark.parametrize("value", [0, -1])
def test_batas_dan_ttl_harus_positif(field, value):
    with pytest.raises(ValidationError, match=field):
        _settings(**{field: value})


def test_sources_mode_selain_mock_atau_live_ditolak():
    with pytest.raises(ValidationError, match="sources_mode"):
        _settings(sources_mode="campur")


# --- (a) load_api_key: dites langsung, tanpa SOURCES_MODE -----------------


@pytest.mark.parametrize(
    "content", [LEAKY_KEY, LEAKY_KEY + "\n", f"  {LEAKY_KEY} \r\n"]
)
def test_load_api_key_valid_dikembalikan_sebagai_secretstr_tanpa_whitespace(
    tmp_path, content
):
    key = load_api_key(_key_file(tmp_path, "k.txt", content), ABUSE_VAR)

    assert isinstance(key, SecretStr)
    assert key.get_secret_value() == LEAKY_KEY
    assert LEAKY_KEY not in repr(key)
    assert LEAKY_KEY not in str(key)


def test_load_api_key_file_hilang(tmp_path):
    with pytest.raises(SecretFileError, match=ABUSE_VAR) as exc:
        load_api_key(tmp_path / "tidak-ada.txt", ABUSE_VAR)

    assert "tidak ditemukan" in str(exc.value)
    assert "tidak-ada" not in str(exc.value)  # path juga tidak ikut dicetak


def test_load_api_key_path_berupa_folder_diperlakukan_tidak_terbaca(tmp_path):
    with pytest.raises(SecretFileError, match=VT_VAR):
        load_api_key(tmp_path, VT_VAR)


@pytest.mark.parametrize("content", ["", "\n", "   \n\t\r\n"])
def test_load_api_key_file_kosong_atau_hanya_whitespace(tmp_path, content):
    with pytest.raises(SecretFileError, match="kosong") as exc:
        load_api_key(_key_file(tmp_path, "k.txt", content), VT_VAR)

    assert VT_VAR in str(exc.value)


@pytest.mark.parametrize(
    "content", ["ganti-dengan-api-key", "GANTI-x\n", "  Ganti-Saya  "]
)
def test_load_api_key_placeholder_ditolak(tmp_path, content):
    with pytest.raises(SecretFileError, match="nilai contoh") as exc:
        load_api_key(_key_file(tmp_path, "k.txt", content), ABUSE_VAR)

    assert ABUSE_VAR in str(exc.value)
    assert content.strip() not in str(exc.value)


@pytest.mark.parametrize(
    "content",
    [
        f"{LEAKY_KEY}\nbaris-kedua",
        f"{LEAKY_KEY} {LEAKY_KEY}",
        f"{LEAKY_KEY}\tx",
        LEAKY_KEY + "é",
    ],
)
def test_load_api_key_isi_bukan_satu_key_ditolak_tanpa_bocor(tmp_path, content):
    with pytest.raises(SecretFileError, match="satu API key") as exc:
        load_api_key(_key_file(tmp_path, "k.txt", content), ABUSE_VAR)

    assert "KEY-UJI-RAHASIA" not in _rendered(exc)


def test_load_api_key_bukan_utf8_tidak_membocorkan_byte(tmp_path):
    # UnicodeDecodeError bawaan menyertakan byte yang gagal didekode; tidak boleh ikut.
    path = _key_file(tmp_path, "k.bin", LEAKY_KEY.encode() + b"\xff\xfe")

    with pytest.raises(SecretFileError, match=ABUSE_VAR) as exc:
        load_api_key(path, ABUSE_VAR)

    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__ is True
    assert "KEY-UJI-RAHASIA" not in _rendered(exc)


# --- Properti Settings membaca file yang sama -----------------------------


def test_properti_key_membaca_isi_file_masing_masing(tmp_path):
    s = _settings(
        abuseipdb_api_key_file=_key_file(tmp_path, "a.txt", "kunci-abuse\n"),
        virustotal_api_key_file=_key_file(tmp_path, "v.txt", "kunci-vt\n"),
    )

    assert s.abuseipdb_api_key.get_secret_value() == "kunci-abuse"
    assert s.virustotal_api_key.get_secret_value() == "kunci-vt"


# --- Mode mock: isi file tidak dipakai ------------------------------------


def test_mode_mock_menerima_file_key_hilang_kosong_atau_placeholder(tmp_path):
    s = _settings(
        sources_mode="mock",
        abuseipdb_api_key_file=tmp_path / "tidak-ada.txt",
        virustotal_api_key_file=_key_file(tmp_path, "v.txt", ""),
    )
    assert s.sources_mode == "mock"

    s = _settings(
        abuseipdb_api_key_file=_key_file(tmp_path, "a.txt", "ganti-dengan-api-key"),
        virustotal_api_key_file=_key_file(tmp_path, "v2.txt", "ganti-dengan-api-key"),
    )
    assert s.sources_mode == "mock"


# --- Mode live: validasi file key --------------------------------------------


def _live(tmp_path, abuse: str | None, vt: str | None) -> Settings:
    """Settings live; `None` = file tidak dibuat."""
    paths = {}
    for name, content in (("abuseipdb", abuse), ("virustotal", vt)):
        path = tmp_path / f"{name}.txt"
        if content is not None:
            path.write_text(content, encoding="utf-8")
        paths[f"{name}_api_key_file"] = path
    return _settings(sources_mode="live", **paths)


@pytest.mark.parametrize(
    ("abuse", "vt", "bermasalah", "aman"),
    [
        (None, LEAKY_KEY, ABUSE_VAR, VT_VAR),
        ("", LEAKY_KEY, ABUSE_VAR, VT_VAR),
        ("ganti-dengan-api-key", LEAKY_KEY, ABUSE_VAR, VT_VAR),
        (LEAKY_KEY, None, VT_VAR, ABUSE_VAR),
        (LEAKY_KEY, "\n", VT_VAR, ABUSE_VAR),
        (LEAKY_KEY, "ganti-x", VT_VAR, ABUSE_VAR),
    ],
)
def test_live_file_key_bermasalah_menyebut_hanya_variabel_yang_bermasalah(
    tmp_path, abuse, vt, bermasalah, aman
):
    with pytest.raises(ValidationError) as exc:
        _live(tmp_path, abuse, vt)

    text = _rendered(exc)
    assert bermasalah in text
    assert aman not in text
    assert "KEY-UJI-RAHASIA" not in text


def test_live_kedua_file_bermasalah_dilaporkan_bersamaan(tmp_path):
    with pytest.raises(ValidationError) as exc:
        _live(tmp_path, None, "")

    assert ABUSE_VAR in str(exc.value)
    assert VT_VAR in str(exc.value)


# --- Mode live dengan file key valid diterima (guard sementara dicabut di Tahap 3) -----


def test_live_dengan_file_key_valid_diterima(tmp_path):
    s = _live(tmp_path, LEAKY_KEY, LEAKY_KEY + "2")

    assert s.sources_mode == "live"
    assert s.abuseipdb_api_key.get_secret_value() == LEAKY_KEY
    assert LEAKY_KEY not in repr(s)  # key tidak ikut tercetak lewat repr Settings


# --- Start nyata: pesan di keluaran proses --------------------------------


def _start(tmp_path, **env) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        check=False,  # returncode diperiksa sendiri oleh tiap test
        cwd=BACKEND_DIR,
        env={**os.environ, "JWT_SECRET_KEY": VALID_JWT, **env},
        capture_output=True,
        text=True,
        timeout=90,
    )


def test_start_live_dengan_key_valid_normal_tanpa_bocor(tmp_path):
    proc = _start(
        tmp_path,
        SOURCES_MODE="live",
        ABUSEIPDB_API_KEY_FILE=str(_key_file(tmp_path, "a.txt", LEAKY_KEY)),
        VIRUSTOTAL_API_KEY_FILE=str(_key_file(tmp_path, "v.txt", LEAKY_KEY)),
    )

    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aplikasi dimulai" in out
    assert "sources_mode=live" in out
    assert "KEY-UJI-RAHASIA" not in out


def test_start_live_dengan_file_key_hilang_menyebut_nama_variabel(tmp_path):
    proc = _start(
        tmp_path,
        SOURCES_MODE="live",
        ABUSEIPDB_API_KEY_FILE=str(tmp_path / "tidak-ada.txt"),
        VIRUSTOTAL_API_KEY_FILE=str(_key_file(tmp_path, "v.txt", LEAKY_KEY)),
    )

    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert ABUSE_VAR in out
    assert "tidak-ada" not in out
    assert "KEY-UJI-RAHASIA" not in out


def test_start_mock_dengan_file_key_kosong_normal(tmp_path):
    proc = _start(
        tmp_path,
        SOURCES_MODE="mock",
        ABUSEIPDB_API_KEY_FILE=str(_key_file(tmp_path, "a.txt", "")),
        VIRUSTOTAL_API_KEY_FILE=str(tmp_path / "tidak-ada.txt"),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "aplikasi dimulai" in proc.stdout + proc.stderr
