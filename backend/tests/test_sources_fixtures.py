"""Fixture respons sumber (TASK-02 Tahap 1): berlabel nyata/simulasi dan bebas data kontak.

Aturan CLAUDE.md: jangan menyimpan data kontak (whois, RDAP, email/telepon) di fixture.
"""

import json
import re

import pytest

from tests.sources_support import FIXTURE_DIR

FILES = sorted(p for p in FIXTURE_DIR.iterdir() if p.is_file())
FORBIDDEN_WORDS = (
    "whois",
    "rdap",
    "last_analysis_results",
    "email",
    "e-mail",
    "phone",
    "telepon",
    "vcard",
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def test_direktori_fixture_tidak_kosong():
    assert FILES


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_nama_fixture_berlabel_nyata_atau_simulasi(path):
    assert "_nyata_" in path.name or "simulasi" in path.name


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_fixture_tidak_memuat_data_kontak_atau_data_besar(path):
    text = path.read_text(encoding="utf-8")

    assert EMAIL.search(text) is None
    for word in FORBIDDEN_WORDS:
        assert word not in text.lower()


@pytest.mark.parametrize(
    "path", [p for p in FILES if p.suffix == ".json"], ids=lambda p: p.name
)
def test_fixture_json_valid(path):
    json.loads(path.read_text(encoding="utf-8"))


# Kasus simulasi Bab 9 (rencana Tahap 1, butir 7) -> fixture yang mewakilinya. "Timeout" tidak
# berupa file: ia exception httpx (`raises(httpx.ReadTimeout)`) di test kedua adapter.
KASUS_BAB_9 = {
    "skor 0": ["abuseipdb_simulasi_skor_0_ada_laporan.json"],
    "nol laporan": ["abuseipdb_simulasi_skor_0_nol_laporan.json"],
    "objek tidak ditemukan": ["virustotal_simulasi_tidak_ditemukan_404.json"],
    "statistik kosong": ["virustotal_simulasi_stats_kosong.json"],
    "all-undetected": ["virustotal_simulasi_all_undetected.json"],
    "all-timeout": ["virustotal_simulasi_all_timeout.json"],
    "field hilang": [
        "abuseipdb_simulasi_field_hilang.json",
        "virustotal_simulasi_field_hilang.json",
    ],
    "401": ["abuseipdb_simulasi_401.json", "virustotal_simulasi_401.json"],
    "403": ["abuseipdb_simulasi_403.json", "virustotal_simulasi_403.json"],
    "429": ["abuseipdb_simulasi_429.json", "virustotal_simulasi_429.json"],
    "JSON rusak": ["simulasi_json_rusak.txt"],
}


@pytest.mark.parametrize("kasus", KASUS_BAB_9)
def test_fixture_simulasi_mencakup_kasus_bab_9(kasus):
    for name in KASUS_BAB_9[kasus]:
        assert (FIXTURE_DIR / name).is_file(), f"fixture untuk '{kasus}' hilang: {name}"


def test_fixture_nyata_dari_ip_dan_tanggal_yang_tercatat():
    nyata = [p.name for p in FILES if "_nyata_" in p.name]

    assert nyata
    assert all("2026-10-29_118.25.6.39" in name for name in nyata)
