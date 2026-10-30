"""Skor gabungan, label, flag, dan `assess()` (TASK-02 Tahap 2; contoh Bab 4 dan Bab 9).

`12 malicious -> V=96` dan `13 -> 100` sudah diuji di `test_sources_virustotal.py` (Tahap 1).
Bobot, koefisien, dan ambang di sini berstatus percobaan; mengubahnya butuh keputusan tim.
"""

import json
from datetime import UTC, datetime

import pytest

from app.services import ip_checks, scoring
from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    FLAG_SUMBER_SIMULASI,
    REASON_REQUIRED_STATUSES,
    SCORED_STATUSES,
    SourceReason,
    SourceResult,
    SourceStatus,
)
from app.services.sources.factory import get_sources
from tests.sources_support import (
    NOW,
    NYATA_ABUSEIPDB,
    NYATA_VIRUSTOTAL,
    live_adapters,
    reply,
)

A, V = "abuseipdb", "virustotal"


def src(
    name: str,
    status: SourceStatus = SourceStatus.OK_SIGNAL,
    score: int | None = 0,
    *,
    evidence: dict | None = None,
    flags: tuple[str, ...] = (),
) -> SourceResult:
    if status not in SCORED_STATUSES:
        score = None
    reason = SourceReason.TIMEOUT if status in REASON_REQUIRED_STATUSES else None
    return SourceResult(
        source=name,
        status=status,
        reason=reason,
        normalized_score=score,
        evidence_summary=evidence or {},
        flags=flags,
    )


def pair(a: int, v: int) -> list[SourceResult]:
    return [src(A, score=a), src(V, score=v)]


# --- skor gabungan ----------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "v", "expected"),
    [
        (90, 80, 85.4545),
        (90, 0, 49.0909),
        (0, 0, 0.0),
        (7, 0, 3.8181),
        (100, 100, 100.0),
        (0, 100, 45.4545),
    ],
)
def test_rumus_30a_ditambah_25v_dibagi_55(a, v, expected):
    assert scoring.combined_score(pair(a, v)) == pytest.approx(expected, abs=1e-4)


def test_pembulatan_contoh_bab_4():
    assert round(scoring.combined_score(pair(90, 80)), 1) == 85.5
    assert round(scoring.combined_score(pair(90, 0)), 1) == 49.1
    assert round(scoring.combined_score(pair(7, 0)), 1) == 3.8


def test_sumber_dicari_berdasarkan_nama_bukan_urutan():
    assert scoring.combined_score(list(reversed(pair(90, 0)))) == pytest.approx(
        scoring.combined_score(pair(90, 0))
    )


@pytest.mark.parametrize(
    "status",
    [
        SourceStatus.NO_RECORD,
        SourceStatus.INSUFFICIENT_DATA,
        SourceStatus.ERROR,
        SourceStatus.SKIPPED,
    ],
)
def test_skor_null_bila_salah_satu_sumber_tidak_bisa_dinilai(status):
    assert scoring.combined_score([src(A, score=90), src(V, status)]) is None
    assert scoring.combined_score([src(A, status), src(V, score=80)]) is None
    assert scoring.combined_score([src(A, status), src(V, status)]) is None


def test_skor_null_bila_sumber_tidak_lengkap():
    assert scoring.combined_score([]) is None
    assert scoring.combined_score([src(A, score=90)]) is None
    assert scoring.combined_score([src("otx", score=90), src(V, score=80)]) is None


# --- label ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.0, "RENDAH"),
        (24.99, "RENDAH"),
        (25.0, "PERLU_PEMERIKSAAN"),
        (49.99, "PERLU_PEMERIKSAAN"),
        (50.0, "TINGGI"),
        (74.96, "TINGGI"),  # tampil 75.0 di API, label tetap dari nilai asli
        (75.0, "SANGAT_TINGGI"),
        (100.0, "SANGAT_TINGGI"),
        (None, None),
    ],
)
def test_batas_label_dari_nilai_sebelum_pembulatan(score, label):
    assert scoring.indication(score) == label


@pytest.mark.parametrize(
    ("a_v", "score", "label"),
    [
        (24, 24.0, "RENDAH"),
        (25, 25.0, "PERLU_PEMERIKSAAN"),
        (50, 50.0, "TINGGI"),
        (75, 75.0, "SANGAT_TINGGI"),
    ],
)
def test_batas_label_tepat_di_25_50_75_lewat_rumus(a_v, score, label):
    # A = V = n menghasilkan tepat n (55n/55), jadi batas tidak bergantung pada pembulatan float.
    combined = scoring.combined_score(pair(a_v, a_v))

    assert combined == score
    assert scoring.indication(combined) == label


# --- flag -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "v", "expected"),
    [(90, 0, True), (50, 0, True), (0, 50, True), (49, 0, False), (90, 80, False)],
)
def test_hasil_berbeda_jika_selisih_50_atau_lebih(a, v, expected):
    assert (scoring.FLAG_HASIL_BERBEDA in scoring.derive_flags(pair(a, v))) is expected


def test_hasil_berbeda_butuh_kedua_sumber_tersedia():
    flags = scoring.derive_flags([src(A, score=90), src(V, SourceStatus.ERROR)])

    assert scoring.FLAG_HASIL_BERBEDA not in flags


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ({"isWhitelisted": True}, True),
        ({"isWhitelisted": False}, False),
        ({"isWhitelisted": None}, False),  # null: tidak ada flag
        ({}, False),
    ],
)
def test_whitelisted_hanya_jika_is_whitelisted_true(evidence, expected):
    results = [src(A, score=90, evidence=evidence), src(V, score=80)]

    assert (scoring.FLAG_WHITELISTED in scoring.derive_flags(results)) is expected


def test_whitelisted_tidak_memangkas_skor():
    plain = pair(90, 80)
    whitelisted = [src(A, score=90, evidence={"isWhitelisted": True}), src(V, score=80)]

    assert scoring.combined_score(whitelisted) == scoring.combined_score(plain)


def test_whitelisted_hanya_dari_abuseipdb():
    results = [src(A, score=90), src(V, score=80, evidence={"isWhitelisted": True})]

    assert scoring.FLAG_WHITELISTED not in scoring.derive_flags(results)


def test_no_vendor_opinion_diteruskan_dari_virustotal():
    results = [src(A, score=0), src(V, score=0, flags=(FLAG_NO_VENDOR_OPINION,))]

    assert scoring.derive_flags(results) == [FLAG_NO_VENDOR_OPINION]


def test_sumber_simulasi_terbawa_walau_tidak_ada_sumber_yang_bisa_dinilai():
    # Cek simulasi yang TIDAK_TERSEDIA tetap harus ber-flag, kalau tidak lolos dari guard MISP.
    results = [
        src(A, SourceStatus.ERROR, flags=(FLAG_SUMBER_SIMULASI,)),
        src(V, SourceStatus.NO_RECORD, flags=(FLAG_SUMBER_SIMULASI,)),
    ]

    assert scoring.derive_flags(results) == [FLAG_SUMBER_SIMULASI]


def test_urutan_flag_tetap_dan_tanpa_duplikat():
    results = [
        src(
            A,
            score=90,
            evidence={"isWhitelisted": True},
            flags=(FLAG_SUMBER_SIMULASI,),
        ),
        src(V, score=0, flags=(FLAG_SUMBER_SIMULASI, FLAG_NO_VENDOR_OPINION)),
    ]

    assert scoring.derive_flags(results) == [
        "HASIL_BERBEDA",
        "NO_VENDOR_OPINION",
        "WHITELISTED",
        "SUMBER_SIMULASI",
    ]


def test_flag_tak_dikenal_dari_sumber_tidak_diteruskan():
    results = [src(A, score=0, flags=("FLAG_ASING",)), src(V, score=0)]

    assert scoring.derive_flags(results) == []


# --- assess(): cakupan dan status -------------------------------------------------

NON_SCORED = [
    SourceStatus.NO_RECORD,
    SourceStatus.INSUFFICIENT_DATA,
    SourceStatus.ERROR,
    SourceStatus.SKIPPED,
]


@pytest.mark.parametrize("status", NON_SCORED)
def test_status_non_ok_tidak_menambah_cakupan(status):
    none = ip_checks.assess([src(A, status), src(V, status)])
    one = ip_checks.assess([src(A, score=10), src(V, status)])

    assert (none.assessment_status, none.coverage, none.risk_score) == (
        "TIDAK_TERSEDIA",
        "0/2",
        None,
    )
    assert (one.assessment_status, one.coverage, one.risk_score) == (
        "DATA_TERBATAS",
        "1/2",
        None,
    )


@pytest.mark.parametrize("status", [SourceStatus.OK_SIGNAL, SourceStatus.OK_NO_SIGNAL])
def test_hanya_ok_signal_dan_ok_no_signal_menambah_cakupan(status):
    result = ip_checks.assess([src(A, status), src(V, status)])

    assert (result.assessment_status, result.coverage) == ("COMPLETE", "2/2")
    assert result.risk_score is not None


def test_tanpa_hasil_sumber_adalah_tidak_tersedia_bukan_complete():
    result = ip_checks.assess([])

    assert (result.assessment_status, result.coverage, result.risk_score) == (
        "TIDAK_TERSEDIA",
        "0/0",
        None,
    )


# --- contoh Bab 4 melalui adapter mock ----------------------------------------------

DEMO = [
    # ip, skor dibulatkan, assessment_status, coverage, label, flag
    ("1.1.1.1", 85.5, "COMPLETE", "2/2", "SANGAT_TINGGI", ["SUMBER_SIMULASI"]),
    (
        "1.0.0.1",
        49.1,
        "COMPLETE",
        "2/2",
        "PERLU_PEMERIKSAAN",
        ["HASIL_BERBEDA", "SUMBER_SIMULASI"],
    ),
    ("8.8.8.8", None, "DATA_TERBATAS", "1/2", None, ["SUMBER_SIMULASI"]),
    ("8.8.4.4", None, "TIDAK_TERSEDIA", "0/2", None, ["SUMBER_SIMULASI"]),
    (
        "9.9.9.9",
        85.5,
        "COMPLETE",
        "2/2",
        "SANGAT_TINGGI",
        ["WHITELISTED", "SUMBER_SIMULASI"],
    ),
    (
        "149.112.112.112",
        0.0,
        "COMPLETE",
        "2/2",
        "RENDAH",
        ["NO_VENDOR_OPINION", "SUMBER_SIMULASI"],
    ),
    ("208.67.222.222", None, "DATA_TERBATAS", "1/2", None, ["SUMBER_SIMULASI"]),
    ("93.184.216.34", 0.0, "COMPLETE", "2/2", "RENDAH", ["SUMBER_SIMULASI"]),
]


@pytest.mark.parametrize(("ip", "score", "status", "coverage", "label", "flags"), DEMO)
def test_contoh_bab_4_lewat_adapter_mock(ip, score, status, coverage, label, flags):
    results = ip_checks.collect_sources(ip, get_sources())
    assessment = ip_checks.assess(results)

    assert assessment.assessment_status == status
    assert assessment.coverage == coverage
    assert assessment.flags == flags
    if score is None:
        assert assessment.risk_score is None
    else:
        assert round(assessment.risk_score, 1) == score
    assert scoring.indication(assessment.risk_score) == label


# --- data respons nyata 29 Okt 2026 -----------------------------------------------------


def test_data_nyata_a7_v0_menjadi_3_8_rendah_complete_tanpa_hasil_berbeda():
    results = ip_checks.collect_sources(
        "118.25.6.39",
        live_adapters(
            reply(200, fixture=NYATA_ABUSEIPDB), reply(200, fixture=NYATA_VIRUSTOTAL)
        ),
    )
    assessment = ip_checks.assess(results)

    assert [r.normalized_score for r in results] == [7, 0]
    assert round(assessment.risk_score, 1) == 3.8
    assert scoring.indication(assessment.risk_score) == "RENDAH"
    assert (assessment.assessment_status, assessment.coverage) == ("COMPLETE", "2/2")
    assert assessment.flags == []  # tanpa HASIL_BERBEDA dan tanpa SUMBER_SIMULASI


# --- bentuk tersimpan -------------------------------------------------------------------


@pytest.mark.parametrize("ip", [row[0] for row in DEMO])
def test_hasil_tersimpan_bisa_di_jsonkan_dan_waktunya_utc(ip):
    stored = [
        ip_checks.to_stored(r) for r in ip_checks.collect_sources(ip, get_sources())
    ]

    decoded = json.loads(json.dumps(stored))  # JSONB memakai json.dumps

    assert decoded == stored
    for item in decoded:
        assert item["retrieved_at"] is not None
        assert (
            datetime.fromisoformat(item["retrieved_at"]).utcoffset().total_seconds()
            == 0
        )
        assert isinstance(item["flags"], list)


def test_to_stored_menyimpan_semua_field_hasil():
    result = ip_checks.collect_sources(
        "118.25.6.39",
        live_adapters(
            reply(200, fixture=NYATA_ABUSEIPDB), reply(200, fixture=NYATA_VIRUSTOTAL)
        ),
    )[0]

    stored = ip_checks.to_stored(result)

    assert stored["status"] == "OK_SIGNAL"
    assert stored["reason"] is None
    assert stored["normalized_score"] == 7
    assert stored["source_time"] == "2026-09-17T22:17:21+00:00"
    assert stored["source_time_type"] == "last_report"
    assert stored["retrieved_at"] == NOW.astimezone(UTC).isoformat()
    assert stored["evidence_summary"]["abuseConfidenceScore"] == 7
