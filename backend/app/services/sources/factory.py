"""Pemilihan sumber reputasi berdasarkan `SOURCES_MODE`.

Dua lapis dengan tanggung jawab berbeda:
- `build_sources()` murni: membuat adapter (mock atau live), tanpa DB dan tanpa efek samping.
- `get_sources()` dependency FastAPI: membungkus tiap adapter dengan `SourceGateway` (cache dan
  pembatas kuota). Ia hanya menyimpan referensi engine; TIDAK membaca atau menulis cache, tidak
  menyentuh kuota, dan tidak membuat request. Semua itu terjadi di `SourceGateway.fetch`, setelah
  `validate_ip` lolos (dependency berjalan sebelum body diperiksa).
"""

from datetime import timedelta
from functools import lru_cache

import httpx
from sqlalchemy import Engine

from app.core.config import get_settings
from app.core.deps import DbSession
from app.services.sources import abuseipdb, virustotal
from app.services.sources.base import ReputationSource
from app.services.sources.cache import CacheTtl
from app.services.sources.gateway import SourceGateway
from app.services.sources.mock import MockSource
from app.services.sources.quota import QuotaPolicy

# Urutan tetap: hasil per sumber di respons dan DB selalu AbuseIPDB lalu VirusTotal.
SOURCE_NAMES = (abuseipdb.SOURCE_NAME, virustotal.SOURCE_NAME)


@lru_cache
def get_http_client() -> httpx.Client:
    # Verifikasi TLS tetap aktif (bawaan httpx) dan redirect tidak diikuti (bawaan). Timeout
    # per request ditetapkan adapter.
    return httpx.Client()


def close_http_client() -> None:
    if get_http_client.cache_info().currsize:
        get_http_client().close()
        get_http_client.cache_clear()


def build_sources() -> list[ReputationSource]:
    settings = get_settings()
    if settings.sources_mode == "mock":
        return [MockSource(name) for name in SOURCE_NAMES]
    client = get_http_client()
    return [
        abuseipdb.AbuseIpdbSource(
            client,
            settings.abuseipdb_api_key,
            max_age_days=settings.abuseipdb_max_age_days,
            timeout_seconds=settings.source_timeout_seconds,
        ),
        virustotal.VirusTotalSource(
            client,
            settings.virustotal_api_key,
            timeout_seconds=settings.source_timeout_seconds,
        ),
    ]


def build_gateways(engine: Engine) -> list[SourceGateway]:
    """Adapter (mock atau live) yang dibungkus cache dan pembatas kuota bersama.

    Dipakai `get_sources` (API) dan skrip smoke, supaya keduanya melewati limiter dan tabel
    `source_calls` yang sama. Membuatnya tidak membaca/menulis DB dan tidak membuat request.
    """
    settings = get_settings()
    ttl = CacheTtl(
        ok_signal=timedelta(hours=settings.cache_ttl_ok_signal_hours),
        ok_no_signal=timedelta(hours=settings.cache_ttl_ok_no_signal_hours),
        no_record=timedelta(hours=settings.cache_ttl_no_record_hours),
    )
    params_keys = {
        abuseipdb.SOURCE_NAME: f"maxAgeInDays={settings.abuseipdb_max_age_days}",
        virustotal.SOURCE_NAME: "",
    }
    policies = {
        abuseipdb.SOURCE_NAME: QuotaPolicy(
            daily=settings.abuseipdb_daily_limit, daily_reset_from_header=True
        ),
        virustotal.SOURCE_NAME: QuotaPolicy(
            per_minute=settings.vt_per_minute_limit, daily=settings.vt_daily_limit
        ),
    }
    return [
        SourceGateway(
            source,
            engine=engine,
            mode=settings.sources_mode,
            params_key=params_keys[source.name],
            policy=policies[source.name],
            ttl=ttl,
        )
        for source in build_sources()
    ]


def get_sources(db: DbSession) -> list[ReputationSource]:
    return build_gateways(db.get_bind())  # type: ignore[arg-type]
