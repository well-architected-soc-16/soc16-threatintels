from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

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
