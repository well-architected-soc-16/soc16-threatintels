from pwdlib import PasswordHash

# Argon2id dengan parameter bawaan pwdlib (rekomendasi tutorial resmi FastAPI).
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)
