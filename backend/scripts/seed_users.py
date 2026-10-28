"""Seed 4 user awal dari env. Idempotent: user yang sudah ada tidak diubah.

Jalankan: python -m scripts.seed_users
"""

import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from app.core.secret_policy import PLACEHOLDER_PREFIX, is_placeholder
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Role, User

MIN_PASSWORD_LENGTH = 12

logger = logging.getLogger("seed_users")


class SeedConfigError(Exception):
    """Konfigurasi seed tidak valid. Pesan hanya memuat nama variabel, bukan nilainya."""


@dataclass(frozen=True)
class SeedSpec:
    env_prefix: str
    role: Role
    can_send_misp: bool


SEED_SPECS = (
    SeedSpec("SEED_ADMIN", Role.ADMIN, can_send_misp=False),
    SeedSpec("SEED_ANALYST_MISP", Role.ANALYST, can_send_misp=True),
    SeedSpec("SEED_ANALYST", Role.ANALYST, can_send_misp=False),
    SeedSpec("SEED_VIEWER", Role.VIEWER, can_send_misp=False),
)


@dataclass(frozen=True)
class SeedUser:
    username: str
    password: str
    role: Role
    can_send_misp: bool


def load_seed_users(env: Mapping[str, str]) -> list[SeedUser]:
    """Baca dan validasi semua user seed. Gagal total jika salah satu tidak valid."""
    users: list[SeedUser] = []
    errors: list[str] = []

    for spec in SEED_SPECS:
        user_var = f"{spec.env_prefix}_USER"
        password_var = f"{spec.env_prefix}_PASSWORD"
        username = env.get(user_var, "").strip()
        password = env.get(password_var, "")

        if not username:
            errors.append(f"{user_var} kosong atau belum diset")
        if not password:
            errors.append(f"{password_var} kosong atau belum diset")
        elif is_placeholder(password):
            # Nilai contoh di .env.example diketahui publik (repo public).
            errors.append(
                f"{password_var} masih berisi nilai contoh "
                f"(berawalan '{PLACEHOLDER_PREFIX}'); ganti dengan password sendiri"
            )
        elif len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"{password_var} kurang dari {MIN_PASSWORD_LENGTH} karakter")
        if username and password:
            users.append(SeedUser(username, password, spec.role, spec.can_send_misp))

    usernames = [u.username for u in users]
    if len(set(usernames)) != len(usernames):
        errors.append("username seed harus unik antar user")

    if errors:
        raise SeedConfigError("; ".join(errors))
    return users


def seed(users: list[SeedUser]) -> dict[str, str]:
    """Buat user yang belum ada. Mengembalikan {username: 'dibuat' | 'sudah ada'}."""
    outcome: dict[str, str] = {}
    with get_sessionmaker()() as session:
        for item in users:
            existing = session.scalar(
                select(User).where(User.username == item.username)
            )
            if existing is not None:
                outcome[item.username] = "sudah ada"
                continue
            session.add(
                User(
                    username=item.username,
                    password_hash=hash_password(item.password),
                    role=item.role.value,
                    can_send_misp=item.can_send_misp,
                    is_active=True,
                )
            )
            outcome[item.username] = "dibuat"
        session.commit()
    return outcome


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        users = load_seed_users(os.environ)
    except SeedConfigError as exc:
        logger.error("seed dibatalkan: %s", exc)
        return 1

    for username, status in seed(users).items():
        logger.info("%s: %s", username, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
