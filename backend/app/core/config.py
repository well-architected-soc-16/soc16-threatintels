from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from app.core.secret_policy import (
    JWT_MIN_BYTES,
    PLACEHOLDER_PREFIX,
    SecretFileError,
    is_placeholder,
    load_api_key,
)

ABUSEIPDB_KEY_VARIABLE = "ABUSEIPDB_API_KEY_FILE"
VIRUSTOTAL_KEY_VARIABLE = "VIRUSTOTAL_API_KEY_FILE"


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

    # Sumber reputasi (TASK-02). Satu saklar global untuk kedua sumber.
    sources_mode: Literal["mock", "live"] = "mock"
    # Key dibaca dari file (docker secret), bukan env. Pada mode mock isinya tidak dipakai.
    abuseipdb_api_key_file: Path = Path("/run/secrets/abuseipdb_api_key")
    virustotal_api_key_file: Path = Path("/run/secrets/virustotal_api_key")
    source_timeout_seconds: float = Field(10, gt=0)
    abuseipdb_max_age_days: int = Field(30, ge=1, le=365)  # batas dari docs AbuseIPDB
    # Kuota akun tim, dipakai bersama semua user (satu API key per sumber).
    abuseipdb_daily_limit: int = Field(1000, gt=0)
    vt_daily_limit: int = Field(500, gt=0)
    vt_per_minute_limit: int = Field(4, gt=0)
    # TTL cache: usulan percobaan, belum disepakati tim.
    cache_ttl_ok_signal_hours: int = Field(6, gt=0)
    cache_ttl_ok_no_signal_hours: int = Field(24, gt=0)
    cache_ttl_no_record_hours: int = Field(1, gt=0)

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

    # Urutan definisi = urutan eksekusi: (a) file key dulu, baru (b) guard mode live.
    # Pesan keduanya hanya menyebut nama variabel, tidak pernah path atau isi file.
    @model_validator(mode="after")
    def _file_key_valid_jika_mode_live(self) -> Self:
        if self.sources_mode != "live":
            return self
        problems = []
        for variable, path in (
            (ABUSEIPDB_KEY_VARIABLE, self.abuseipdb_api_key_file),
            (VIRUSTOTAL_KEY_VARIABLE, self.virustotal_api_key_file),
        ):
            try:
                load_api_key(path, variable)
            except SecretFileError as exc:
                problems.append(str(exc))
        if problems:
            raise ValueError("SOURCES_MODE=live: " + "; ".join(problems))
        return self

    # SEMENTARA: dicabut di Tahap 3 TASK-02, saat pembatas kuota sudah ada. Sebelum itu,
    # menyambungkan sumber live ke POST /checks (Tahap 2) berarti memanggil API tanpa limiter.
    @model_validator(mode="after")
    def _tolak_mode_live_sementara(self) -> Self:
        if self.sources_mode == "live":
            raise ValueError(
                "SOURCES_MODE=live belum didukung (menunggu pembatas kuota, Tahap 3 TASK-02); "
                "gunakan SOURCES_MODE=mock"
            )
        return self

    @property
    def abuseipdb_api_key(self) -> SecretStr:
        # Hanya untuk mode live; pada mock file boleh kosong dan properti ini akan menolaknya.
        return load_api_key(self.abuseipdb_api_key_file, ABUSEIPDB_KEY_VARIABLE)

    @property
    def virustotal_api_key(self) -> SecretStr:
        return load_api_key(self.virustotal_api_key_file, VIRUSTOTAL_KEY_VARIABLE)

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
