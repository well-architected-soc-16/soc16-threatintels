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


def test_fixture_nyata_dari_ip_dan_tanggal_yang_tercatat():
    nyata = [p.name for p in FILES if "_nyata_" in p.name]

    assert nyata
    assert all("2026-10-29_118.25.6.39" in name for name in nyata)
