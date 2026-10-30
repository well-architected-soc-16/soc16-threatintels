"""Aturan nilai rahasia yang dipakai bersama oleh konfigurasi aplikasi dan skrip seed.

Repository ini public, jadi nilai contoh di `.env.example` diketahui siapa pun.
Nilai contoh dikenali lewat awalan (bukan dengan membaca `.env.example` saat runtime),
sehingga variasi seperti `GANTI-saya` pun ikut tertangkap.
"""

import re
from pathlib import Path

from pydantic import SecretStr

PLACEHOLDER_PREFIX = "ganti-"
JWT_MIN_BYTES = 32

# API key sumber reputasi dikirim sebagai nilai header. Satu key = ASCII yang tampak,
# tanpa spasi/baris baru; file berisi dua baris akan membuat httpx menolak header itu,
# dan pesan galatnya memuat nilai header.
_API_KEY_FORMAT = re.compile(r"[\x21-\x7e]+")


class SecretFileError(ValueError):
    """File secret bermasalah. Pesan hanya memuat nama variabel, tidak pernah path atau isinya."""


def is_placeholder(value: str) -> bool:
    """True jika nilai masih berupa contoh (berawalan `ganti-`, tanpa membedakan huruf besar/kecil)."""
    return value.strip().lower().startswith(PLACEHOLDER_PREFIX)


def load_api_key(path: Path, variable: str) -> SecretStr:
    """Baca API key dari file secret dan pastikan layak dipakai.

    `variable` adalah nama variabel konfigurasi (mis. `ABUSEIPDB_API_KEY_FILE`) dan satu-satunya
    identitas yang boleh muncul di pesan galat. Galat bawaan (OSError, UnicodeDecodeError) sengaja
    tidak disambung (`from None`): UnicodeDecodeError menyertakan byte yang gagal didekode.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise SecretFileError(
            f"{variable}: file tidak ditemukan atau tidak dapat dibaca"
        ) from None

    key = raw.strip()
    if not key:
        raise SecretFileError(
            f"{variable}: file kosong; isi dengan API key (lihat README)"
        )
    if is_placeholder(key):
        raise SecretFileError(
            f"{variable}: file masih berisi nilai contoh (berawalan '{PLACEHOLDER_PREFIX}'); "
            "isi dengan API key asli"
        )
    if not _API_KEY_FORMAT.fullmatch(key):
        raise SecretFileError(
            f"{variable}: isi file berisi spasi, baris baru, atau karakter non-ASCII; "
            "file harus berisi satu API key saja"
        )
    return SecretStr(key)
