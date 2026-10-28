from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITHM = "HS256"

# Argon2id dengan parameter bawaan pwdlib (rekomendasi tutorial resmi FastAPI).
_password_hash = PasswordHash.recommended()

# Dipakai saat username tidak ditemukan: verifikasi tetap dijalankan terhadap hash
# ini supaya waktu respons tidak membedakan "user tidak ada" dari "password salah".
DUMMY_HASH = _password_hash.hash("dummy-password-untuk-menyamakan-waktu")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(username: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    claims = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(
        claims, settings.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Verifikasi tanda tangan dan masa berlaku. Melempar jwt.InvalidTokenError jika gagal.

    `exp` dan `sub` wajib ada. Klaim `role` hanya informasi; otorisasi selalu
    memakai role yang dibaca ulang dari database.
    """
    return jwt.decode(
        token,
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
