from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from app.core.secret_policy import JWT_MIN_BYTES, PLACEHOLDER_PREFIX, is_placeholder


class Settings(BaseSettings):
    # hide_input_in_errors: pesan ValidationError tidak boleh memuat nilai yang ditolak
    # (nilai itu bisa jadi secret yang hampir benar), karena error masuk ke log/traceback.
    model_config = SettingsConfigDict(
        env_file=None, extra="ignore", hide_input_in_errors=True
    )

    app_env: str = "dev"
    db_host: str = "db"
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password_file: Path
    jwt_secret_key: SecretStr
    jwt_expire_minutes: int = 30
    misp_mode: Literal["mock", "live"] = "mock"
    log_level: str = "INFO"

    @field_validator("jwt_secret_key")
    @classmethod
    def _jwt_secret_harus_kuat(cls, value: SecretStr) -> SecretStr:
        # Pesan hanya menyebut nama variabel dan alasannya, tidak pernah nilainya.
        secret = value.get_secret_value()
        if is_placeholder(secret):
            raise ValueError(
                f"JWT_SECRET_KEY masih berisi nilai contoh (berawalan '{PLACEHOLDER_PREFIX}'); "
                "isi dengan string acak, mis. hasil `openssl rand -hex 32`"
            )
        if len(secret.encode("utf-8")) < JWT_MIN_BYTES:
            raise ValueError(
                f"JWT_SECRET_KEY kurang dari {JWT_MIN_BYTES} byte; "
                "isi dengan string acak, mis. hasil `openssl rand -hex 32`"
            )
        return value

    @property
    def db_password(self) -> str:
        # Isi file diakhiri newline; password sebenarnya tanpa whitespace tepi.
        return self.db_password_file.read_text(encoding="utf-8").strip()

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
