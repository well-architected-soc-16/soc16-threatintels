"""Aturan nilai rahasia yang dipakai bersama oleh konfigurasi aplikasi dan skrip seed.

Repository ini public, jadi nilai contoh di `.env.example` diketahui siapa pun.
Nilai contoh dikenali lewat awalan (bukan dengan membaca `.env.example` saat runtime),
sehingga variasi seperti `GANTI-saya` pun ikut tertangkap.
"""

PLACEHOLDER_PREFIX = "ganti-"
JWT_MIN_BYTES = 32


def is_placeholder(value: str) -> bool:
    """True jika nilai masih berupa contoh (berawalan `ganti-`, tanpa membedakan huruf besar/kecil)."""
    return value.strip().lower().startswith(PLACEHOLDER_PREFIX)
