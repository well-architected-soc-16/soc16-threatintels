"""Pemilihan sumber (TASK-02 Tahap 3): builder murni, dependency berlapis gerbang, klien HTTP bersama."""

from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.services.sources import factory
from app.services.sources.abuseipdb import AbuseIpdbSource
from app.services.sources.gateway import SourceGateway
from app.services.sources.mock import MockSource
from app.services.sources.virustotal import VirusTotalSource

KEY_A = "KEY-UJI-ABUSE-0123456789"
KEY_V = "KEY-UJI-VT-0123456789"


def settings_for(tmp_path: Path, mode: str) -> Settings:
    a = tmp_path / "a.txt"
    v = tmp_path / "v.txt"
    a.write_text(KEY_A, encoding="utf-8")
    v.write_text(KEY_V, encoding="utf-8")
    return Settings(
        jwt_secret_key="k" * 32,
        db_name="x",
        db_user="x",
        db_password_file=Path("/tidak/dibaca"),
        sources_mode=mode,
        abuseipdb_api_key_file=a,
        virustotal_api_key_file=v,
        abuseipdb_max_age_days=45,
    )


@pytest.fixture(autouse=True)
def _tutup_klien():
    yield
    factory.close_http_client()


def test_build_sources_mock_urutan_tetap_dan_tanpa_efek_samping():
    sources = factory.build_sources()

    assert [type(s) for s in sources] == [MockSource, MockSource]
    assert [s.name for s in sources] == ["abuseipdb", "virustotal"]


def test_build_sources_live_memakai_adapter_asli_dan_satu_klien_bersama(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(factory, "get_settings", lambda: settings_for(tmp_path, "live"))

    abuse, vt = factory.build_sources()

    assert isinstance(abuse, AbuseIpdbSource) and isinstance(vt, VirusTotalSource)
    assert abuse._client is vt._client is factory.get_http_client()
    assert abuse._max_age_days == 45  # dari konfigurasi, bukan angka tetap
    assert KEY_A not in repr(abuse) and KEY_V not in repr(vt)


def test_klien_http_tidak_mengikuti_redirect_dan_ditutup_saat_shutdown():
    client = factory.get_http_client()

    assert client.follow_redirects is False
    assert factory.get_http_client() is client  # satu instance bersama

    factory.close_http_client()

    assert client.is_closed
    assert factory.get_http_client() is not client  # dibuat ulang bila perlu


def test_get_sources_membungkus_setiap_sumber_dengan_gerbang_mode_mock(db):
    sources = factory.get_sources(db)

    assert [type(s) for s in sources] == [SourceGateway, SourceGateway]
    assert [s.name for s in sources] == ["abuseipdb", "virustotal"]
    assert {s._mode for s in sources} == {"mock"}


def test_get_sources_live_params_key_kuota_dan_ttl_dari_konfigurasi(
    db, tmp_path, monkeypatch
):
    monkeypatch.setattr(factory, "get_settings", lambda: settings_for(tmp_path, "live"))

    abuse, vt = factory.get_sources(db)

    assert {abuse._mode, vt._mode} == {"live"}
    assert (
        abuse._params_key == "maxAgeInDays=45"
    )  # mengikuti parameter yang dikirim adapter
    assert vt._params_key == ""
    assert (abuse._policy.daily, abuse._policy.daily_reset_from_header) == (1000, True)
    assert (vt._policy.per_minute, vt._policy.daily) == (4, 500)
    assert abuse._ttl.ok_signal == timedelta(hours=6)
    assert vt._ttl.ok_no_signal == timedelta(hours=24)
    assert vt._ttl.no_record == timedelta(hours=1)


def test_get_sources_live_tidak_membuat_request_atau_membuka_koneksi(
    db, tmp_path, monkeypatch
):
    import socket

    monkeypatch.setattr(factory, "get_settings", lambda: settings_for(tmp_path, "live"))

    def terlarang(*args, **kwargs):
        raise AssertionError("membangun sumber tidak boleh membuka koneksi")

    monkeypatch.setattr(socket.socket, "connect", terlarang)
    monkeypatch.setattr(httpx.Client, "send", terlarang)

    assert len(factory.get_sources(db)) == 2
