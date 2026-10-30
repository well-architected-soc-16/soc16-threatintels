"""Pemilihan sumber reputasi berdasarkan `SOURCES_MODE`. Dipakai sebagai dependency FastAPI."""

from app.core.config import get_settings
from app.services.sources import abuseipdb, virustotal
from app.services.sources.base import ReputationSource
from app.services.sources.mock import MockSource

# Urutan tetap: hasil per sumber di respons dan DB selalu AbuseIPDB lalu VirusTotal.
SOURCE_NAMES = (abuseipdb.SOURCE_NAME, virustotal.SOURCE_NAME)


def get_sources() -> list[ReputationSource]:
    if get_settings().sources_mode == "mock":
        return [MockSource(name) for name in SOURCE_NAMES]
    # Fail closed: adapter live tidak boleh dipakai sebelum pembatas kuota ada (Tahap 3).
    # `Settings` sudah menolak SOURCES_MODE=live; ini lapisan kedua bila guard itu dicabut lebih dulu.
    raise RuntimeError("SOURCES_MODE=live belum didukung (menunggu Tahap 3 TASK-02)")
