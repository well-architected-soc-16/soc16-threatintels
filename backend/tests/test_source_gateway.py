"""Cache dan pembatas kuota bersama (TASK-02 Tahap 3), diuji langsung pada `SourceGateway`.

Memakai database test sungguhan (advisory lock, UNIQUE, dan transaksi tidak bisa ditiru mock),
sumber palsu yang mencatat pemanggilan, dan jam palsu yang bisa dimajukan.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import SourceCache, SourceCall
from app.services.sources.base import (
    FLAG_NO_VENDOR_OPINION,
    FLAG_SUMBER_SIMULASI,
    SourceReason,
    SourceStatus,
)
from app.services.sources.quota import QuotaPolicy, daily_window_start
from tests.sources_support import (
    ABUSE_POLICY,
    T0,
    VT_POLICY,
    Clock,
    FakeSource,
    make_gateway,
    result_of,
)

A, V = "abuseipdb", "virustotal"
IPS = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "4.4.4.4", "5.5.5.5", "6.6.6.6", "7.7.7.7"]


@pytest.fixture(autouse=True)
def _bersih(db):
    """`db` men-TRUNCATE semua tabel (termasuk source_cache dan source_calls) sebelum tiap test."""


def count(engine, model, *where) -> int:
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(model).where(*where)) or 0
        )


def calls_in(engine, **filters) -> list[SourceCall]:
    with Session(engine) as session:
        stmt = select(SourceCall).order_by(SourceCall.id)
        for key, value in filters.items():
            stmt = stmt.where(getattr(SourceCall, key) == value)
        return list(session.scalars(stmt))


# --- cache: pemakaian ulang -----------------------------------------------------------------


def test_ip_sama_dua_kali_kedua_dari_cache_tanpa_memanggil_adapter(engine):
    clock = Clock()
    source = FakeSource(V, clock=clock)
    gateway = make_gateway(source, engine, clock=clock)

    first = gateway.fetch("8.8.8.8")
    clock.advance(minutes=30)
    second = gateway.fetch("8.8.8.8")

    assert source.calls == ["8.8.8.8"]  # adapter dipanggil sekali
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.retrieved_at == first.retrieved_at == T0  # waktu pengambilan ASLI
    assert second.expires_at == first.expires_at == T0 + timedelta(hours=6)
    assert (
        second.http_status is None and second.duration_ms is None
    )  # tak ada request baru
    assert (second.status, second.normalized_score) == (
        first.status,
        first.normalized_score,
    )
    assert second.evidence_summary == first.evidence_summary
    assert second.source_time == first.source_time
    assert second.source_time_type == first.source_time_type


def test_cache_hit_tidak_menulis_baris_panggilan_dan_tidak_memakai_kuota(engine):
    clock = Clock()
    gateway = make_gateway(FakeSource(V, clock=clock), engine, clock=clock)

    for _ in range(20):  # jauh di atas batas 4/menit
        result = gateway.fetch("8.8.8.8")

    assert result.status is SourceStatus.OK_SIGNAL  # tak pernah SKIPPED
    assert count(engine, SourceCall) == 1


@pytest.mark.parametrize(
    ("status", "ttl_hours"),
    [
        (SourceStatus.OK_SIGNAL, 6),
        (SourceStatus.OK_NO_SIGNAL, 24),
        (SourceStatus.NO_RECORD, 1),
    ],
)
def test_ttl_per_status_berlaku_tepat_sampai_batasnya(engine, status, ttl_hours):
    clock = Clock()
    source = FakeSource(V, lambda ip: result_of(V, status, 10, retrieved_at=clock()))
    gateway = make_gateway(source, engine, clock=clock)
    gateway.fetch("8.8.8.8")

    clock.advance(hours=ttl_hours, seconds=-1)
    assert gateway.fetch("8.8.8.8").from_cache is True  # satu detik sebelum habis

    clock.advance(seconds=1)
    refetched = gateway.fetch("8.8.8.8")  # tepat di batas: sudah tidak berlaku
    assert refetched.from_cache is False
    assert source.calls == ["8.8.8.8", "8.8.8.8"]


def test_cache_kedaluwarsa_diambil_ulang_dengan_retrieved_at_baru(engine):
    clock = Clock()
    source = FakeSource(V, clock=clock)
    gateway = make_gateway(source, engine, clock=clock)
    first = gateway.fetch("8.8.8.8")

    clock.advance(hours=7)  # lewat TTL 6 jam OK_SIGNAL
    second = gateway.fetch("8.8.8.8")

    assert second.from_cache is False
    assert second.retrieved_at == T0 + timedelta(hours=7) != first.retrieved_at
    assert second.expires_at == T0 + timedelta(hours=13)
    assert count(engine, SourceCache) == 1  # upsert, bukan baris baru


def test_hanya_sumber_yang_kedaluwarsa_yang_diambil_ulang(engine):
    clock = Clock()
    abuse = FakeSource(
        A, lambda ip: result_of(A, SourceStatus.NO_RECORD, retrieved_at=clock())
    )
    vt = FakeSource(
        V, lambda ip: result_of(V, SourceStatus.OK_NO_SIGNAL, 0, retrieved_at=clock())
    )
    gateways = [
        make_gateway(abuse, engine, clock=clock),
        make_gateway(vt, engine, clock=clock),
    ]
    for g in gateways:
        g.fetch("8.8.8.8")

    clock.advance(hours=2)  # NO_RECORD (1 jam) habis; OK_NO_SIGNAL (24 jam) belum
    results = [g.fetch("8.8.8.8") for g in gateways]

    assert [r.from_cache for r in results] == [False, True]
    assert len(abuse.calls) == 2 and len(vt.calls) == 1


# --- cache: yang tidak boleh disimpan -----------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [SourceStatus.ERROR, SourceStatus.INSUFFICIENT_DATA, SourceStatus.SKIPPED],
)
def test_error_insufficient_data_dan_skipped_tidak_pernah_di_cache(engine, status):
    clock = Clock()
    source = FakeSource(V, lambda ip: result_of(V, status, retrieved_at=clock()))
    gateway = make_gateway(source, engine, clock=clock, policy=QuotaPolicy())

    first = gateway.fetch("8.8.8.8")
    second = gateway.fetch("8.8.8.8")

    assert count(engine, SourceCache) == 0
    assert first.from_cache is False and second.from_cache is False
    assert first.expires_at is None
    assert len(source.calls) == 2  # tiap kali diambil ulang


def test_error_setelah_hasil_sukses_tidak_menimpa_atau_keluar_dari_cache(engine):
    clock = Clock()
    responses = iter(
        [
            result_of(V, SourceStatus.OK_SIGNAL, 80, retrieved_at=T0),
            result_of(
                V, SourceStatus.ERROR, reason=SourceReason.TIMEOUT, retrieved_at=T0
            ),
            result_of(V, SourceStatus.OK_SIGNAL, 20, retrieved_at=T0),
        ]
    )
    source = FakeSource(V, lambda ip: next(responses))
    gateway = make_gateway(source, engine, clock=clock, policy=QuotaPolicy())
    gateway.fetch("8.8.8.8")
    clock.advance(hours=7)  # cache habis -> diambil ulang -> ERROR

    error = gateway.fetch("8.8.8.8")
    # Cache lama sudah kedaluwarsa dan tak boleh dipakai; ERROR tidak menggantikannya.
    again = gateway.fetch("8.8.8.8")

    assert error.status is SourceStatus.ERROR and error.from_cache is False
    assert again.status is SourceStatus.OK_SIGNAL and again.from_cache is False
    assert again.normalized_score == 20  # hasil baru, bukan 80 dari cache lama
    assert len(source.calls) == 3


def test_flag_bukti_dan_waktu_ikut_tersimpan_di_cache(engine):
    clock = Clock()
    source = FakeSource(
        V,
        lambda ip: result_of(
            V,
            SourceStatus.OK_NO_SIGNAL,
            0,
            flags=(FLAG_NO_VENDOR_OPINION, FLAG_SUMBER_SIMULASI),
            evidence={"harmless": 0, "undetected": 90, "simulasi": True},
            retrieved_at=clock(),
        ),
    )
    gateway = make_gateway(source, engine, clock=clock)
    first = gateway.fetch("8.8.8.8")

    second = gateway.fetch("8.8.8.8")

    assert second.from_cache is True
    # Tanpa flags di cache, hasil simulasi yang kedua kali lolos dari guard MISP.
    assert second.flags == first.flags == (FLAG_NO_VENDOR_OPINION, FLAG_SUMBER_SIMULASI)
    assert second.evidence_summary == {
        "harmless": 0,
        "undetected": 90,
        "simulasi": True,
    }
    assert second.source_time == first.source_time


def test_params_key_berbeda_tidak_berbagi_cache(engine):
    clock = Clock()
    source = FakeSource(A, clock=clock)
    g30 = make_gateway(source, engine, clock=clock, params_key="maxAgeInDays=30")
    g90 = make_gateway(source, engine, clock=clock, params_key="maxAgeInDays=90")

    g30.fetch("8.8.8.8")
    other = g90.fetch("8.8.8.8")

    assert other.from_cache is False
    assert count(engine, SourceCache) == 2


# --- kuota: VirusTotal 4/menit ----------------------------------------------------------------------


def test_cek_ke_5_dalam_semenit_vt_skipped_quota_internal_abuseipdb_tetap_jalan(engine):
    clock = Clock()
    abuse = FakeSource(A, clock=clock)
    vt = FakeSource(V, clock=clock)
    g_abuse = make_gateway(abuse, engine, clock=clock)
    g_vt = make_gateway(vt, engine, clock=clock)

    outcomes = []
    for ip in IPS[:5]:
        outcomes.append((g_abuse.fetch(ip), g_vt.fetch(ip)))
        clock.advance(seconds=5)

    assert [vt_r.status for _, vt_r in outcomes] == [SourceStatus.OK_SIGNAL] * 4 + [
        SourceStatus.SKIPPED
    ]
    skipped = outcomes[4][1]
    assert skipped.reason is SourceReason.QUOTA_INTERNAL
    assert skipped.normalized_score is None and skipped.http_status is None
    assert [a.status for a, _ in outcomes] == [
        SourceStatus.OK_SIGNAL
    ] * 5  # AbuseIPDB jalan
    assert (
        len(vt.calls) == 4 and len(abuse.calls) == 5
    )  # tak ada request keluar saat SKIPPED


def test_skipped_tidak_di_cache_dan_tidak_dicatat_sebagai_panggilan(engine):
    clock = Clock()
    gateway = make_gateway(FakeSource(V, clock=clock), engine, clock=clock)
    for ip in IPS[:4]:
        gateway.fetch(ip)

    skipped = gateway.fetch(IPS[4])

    assert skipped.status is SourceStatus.SKIPPED
    assert count(engine, SourceCache, SourceCache.ip == IPS[4]) == 0
    assert count(engine, SourceCall) == 4


def test_kuota_pulih_setelah_jendela_satu_menit_lewat(engine):
    clock = Clock()
    vt = FakeSource(V, clock=clock)
    gateway = make_gateway(vt, engine, clock=clock)
    for ip in IPS[:4]:
        gateway.fetch(ip)
    assert gateway.fetch(IPS[4]).status is SourceStatus.SKIPPED

    clock.advance(seconds=61)

    assert gateway.fetch(IPS[4]).status is SourceStatus.OK_SIGNAL


# --- kuota: harian -----------------------------------------------------------------------------------


def test_batas_harian_menolak_lalu_pulih_pada_00_00_utc(engine):
    clock = Clock(datetime(2026, 10, 30, 22, 0, tzinfo=UTC))
    # VirusTotal: reset harian 00:00 UTC.
    policy = QuotaPolicy(daily=3)
    source = FakeSource(V, clock=clock)
    gateway = make_gateway(source, engine, clock=clock, policy=policy)
    for ip in IPS[:3]:
        gateway.fetch(ip)
        clock.advance(minutes=10)

    blocked = gateway.fetch(IPS[3])
    clock.advance(hours=2)  # 00:30 UTC hari berikutnya
    allowed = gateway.fetch(IPS[3])

    assert blocked.reason is SourceReason.QUOTA_INTERNAL
    assert allowed.status is SourceStatus.OK_SIGNAL


def test_batas_harian_default_sesuai_kuota_akun_tim():
    from app.core.config import Settings

    s = Settings(
        db_name="x", db_user="x", db_password_file="/dev/null", jwt_secret_key="k" * 32
    )
    assert (s.abuseipdb_daily_limit, s.vt_daily_limit, s.vt_per_minute_limit) == (
        1000,
        500,
        4,
    )
    assert VT_POLICY == QuotaPolicy(per_minute=4, daily=500)
    assert ABUSE_POLICY.daily == 1000 and ABUSE_POLICY.daily_reset_from_header is True


# --- kuota: reset harian AbuseIPDB mengikuti X-RateLimit-Reset -----------------------------------------


def _abuse_with_header(clock, reset_at):
    return FakeSource(
        A,
        lambda ip: result_of(
            A, retrieved_at=clock(), rate_limit_reset=reset_at, rate_limit_remaining=1
        ),
    )


def test_reset_harian_abuseipdb_mengikuti_header_bukan_tengah_malam(engine):
    # Reset 06:00 UTC (bukan 00:00): header yang diabaikan akan lolos dari test ini.
    clock = Clock(datetime(2026, 10, 30, 5, 0, tzinfo=UTC))
    reset = datetime(2026, 10, 31, 6, 0, tzinfo=UTC)
    abuse = _abuse_with_header(clock, reset)
    gateway = make_gateway(
        abuse,
        engine,
        clock=clock,
        policy=QuotaPolicy(daily=2, daily_reset_from_header=True),
    )
    gateway.fetch(IPS[0])
    clock.advance(minutes=30)
    gateway.fetch(IPS[1])
    clock.advance(minutes=10)
    assert (
        gateway.fetch(IPS[2]).reason is SourceReason.QUOTA_INTERNAL
    )  # 05:40: jendela belum reset

    clock.advance(minutes=21)  # 06:01 UTC: lewat reset 06:00

    assert gateway.fetch(IPS[2]).status is SourceStatus.OK_SIGNAL


def test_tanpa_header_reset_harian_abuseipdb_pada_00_00_utc(engine):
    clock = Clock(datetime(2026, 10, 30, 5, 0, tzinfo=UTC))
    abuse = FakeSource(A, clock=clock)  # respons tanpa X-RateLimit-Reset
    gateway = make_gateway(
        abuse,
        engine,
        clock=clock,
        policy=QuotaPolicy(daily=2, daily_reset_from_header=True),
    )
    gateway.fetch(IPS[0])
    clock.advance(minutes=30)
    gateway.fetch(IPS[1])

    clock.advance(hours=1)  # 06:31 UTC: tanpa header, belum ada reset
    assert gateway.fetch(IPS[2]).reason is SourceReason.QUOTA_INTERNAL

    clock.advance(hours=18)  # 00:31 UTC hari berikutnya
    assert gateway.fetch(IPS[2]).status is SourceStatus.OK_SIGNAL


@pytest.mark.parametrize(
    ("now", "anchor", "expected"),
    [
        (
            datetime(2026, 10, 30, 7, 0, tzinfo=UTC),
            None,
            datetime(2026, 10, 30, 0, 0, tzinfo=UTC),
        ),
        # anchor di masa depan: jendela sekarang dimulai 24 jam sebelum anchor
        (
            datetime(2026, 10, 30, 5, 0, tzinfo=UTC),
            datetime(2026, 10, 31, 6, 0, tzinfo=UTC),
            datetime(2026, 10, 29, 6, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 10, 30, 6, 1, tzinfo=UTC),
            datetime(2026, 10, 31, 6, 0, tzinfo=UTC),
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
        ),
        # anchor di masa lalu (header lama): reset berulang tiap 24 jam dari titik itu
        (
            datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
            datetime(2026, 11, 2, 6, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
        ),
    ],
)
def test_daily_window_start(now, anchor, expected):
    assert daily_window_start(now, anchor) == expected


# --- kuota: 429 dan cooldown ------------------------------------------------------------------------------


def _responds_429(clock, retry_after):
    return FakeSource(
        V,
        lambda ip: result_of(
            V,
            SourceStatus.ERROR,
            reason=SourceReason.RATE_LIMIT,
            retrieved_at=clock(),
            http_status=429,
            retry_after=retry_after,
        ),
    )


@pytest.mark.parametrize(("retry_after", "cooldown"), [(120, 120), (None, 60)])
def test_setelah_429_sumber_di_skip_sampai_cooldown_habis(
    engine, retry_after, cooldown
):
    clock = Clock()
    vt = _responds_429(clock, retry_after)
    gateway = make_gateway(vt, engine, clock=clock, policy=QuotaPolicy())
    first = gateway.fetch(IPS[0])
    assert (first.status, first.reason) == (SourceStatus.ERROR, SourceReason.RATE_LIMIT)
    assert vt.calls == [IPS[0]]  # tidak ada retry pada request yang sama

    clock.advance(seconds=cooldown - 1)
    during = gateway.fetch(IPS[1])
    clock.advance(seconds=2)
    after = gateway.fetch(IPS[1])

    assert (during.status, during.reason) == (
        SourceStatus.SKIPPED,
        SourceReason.QUOTA_INTERNAL,
    )
    assert (
        after.reason is SourceReason.RATE_LIMIT
    )  # diminta lagi (dan 429 lagi), bukan di-skip
    assert vt.calls == [IPS[0], IPS[1]]


def test_cooldown_hanya_untuk_sumber_yang_kena_429(engine):
    clock = Clock()
    vt = _responds_429(clock, 120)
    abuse = FakeSource(A, clock=clock)
    g_vt = make_gateway(vt, engine, clock=clock, policy=QuotaPolicy())
    g_abuse = make_gateway(abuse, engine, clock=clock)
    g_vt.fetch(IPS[0])

    assert g_vt.fetch(IPS[1]).status is SourceStatus.SKIPPED
    assert g_abuse.fetch(IPS[1]).status is SourceStatus.OK_SIGNAL


def test_429_dari_panggilan_mock_tidak_memicu_cooldown_live(engine):
    clock = Clock()
    g_mock = make_gateway(_responds_429(clock, 600), engine, clock=clock, mode="mock")
    g_mock.fetch(IPS[0])
    vt_live = FakeSource(V, clock=clock)
    g_live = make_gateway(vt_live, engine, clock=clock)

    assert g_live.fetch(IPS[1]).status is SourceStatus.OK_SIGNAL


# --- mode mock dan live dipisah ------------------------------------------------------------------------------


def test_mode_live_tidak_membaca_cache_mock_dan_sebaliknya(engine):
    clock = Clock()
    simulated = FakeSource(
        V, lambda ip: result_of(V, flags=(FLAG_SUMBER_SIMULASI,), retrieved_at=clock())
    )
    real = FakeSource(V, clock=clock)
    g_mock = make_gateway(simulated, engine, clock=clock, mode="mock")
    g_live = make_gateway(real, engine, clock=clock, mode="live")
    g_mock.fetch("8.8.8.8")  # baris simulasi ada di cache

    live_result = g_live.fetch("8.8.8.8")
    mock_again = g_mock.fetch("8.8.8.8")

    assert live_result.from_cache is False  # live tetap mengambil dari sumber
    assert FLAG_SUMBER_SIMULASI not in live_result.flags
    assert real.calls == ["8.8.8.8"]
    assert mock_again.from_cache is True and FLAG_SUMBER_SIMULASI in mock_again.flags
    assert sorted(r.mode for r in _cache_rows(engine)) == ["live", "mock"]
    # Baris live yang baru tidak dibaca mock, dan sebaliknya.
    assert simulated.calls == ["8.8.8.8"]


def _cache_rows(engine) -> list[SourceCache]:
    with Session(engine) as session:
        return list(session.scalars(select(SourceCache)))


def test_panggilan_mock_dicatat_tetapi_tidak_pernah_skipped_dan_tidak_dihitung(engine):
    clock = Clock()
    g_mock = make_gateway(FakeSource(V, clock=clock), engine, clock=clock, mode="mock")

    results = [g_mock.fetch(ip) for ip in IPS[:7]]  # jauh di atas 4/menit

    assert all(r.status is SourceStatus.OK_SIGNAL for r in results)
    assert (
        count(engine, SourceCall, SourceCall.mode == "mock") == 7
    )  # dicatat sebagai bukti
    # Baris mock tidak mengurangi kuota live.
    g_live = make_gateway(FakeSource(V, clock=clock), engine, clock=clock, mode="live")
    live = [g_live.fetch(ip).status for ip in IPS[:5]]
    assert live == [SourceStatus.OK_SIGNAL] * 4 + [SourceStatus.SKIPPED]


# --- isi baris source_calls ------------------------------------------------------------------------------------


def test_baris_panggilan_menyimpan_bukti_tanpa_key_header_atau_body(engine):
    clock = Clock()
    reset = datetime(2026, 10, 31, 6, 0, tzinfo=UTC)
    abuse = FakeSource(
        A,
        lambda ip: result_of(
            A,
            SourceStatus.ERROR,
            reason=SourceReason.RATE_LIMIT,
            http_status=429,
            retry_after=30,
            rate_limit_reset=reset,
            rate_limit_remaining=0,
        ),
    )
    make_gateway(abuse, engine, clock=clock, policy=QuotaPolicy()).fetch("8.8.8.8")

    (row,) = calls_in(engine)

    assert (row.source, row.mode, row.called_at) == (A, "live", T0)
    assert (row.http_status, row.result_status, row.reason) == (
        429,
        "ERROR",
        "RATE_LIMIT",
    )
    assert (row.duration_ms, row.retry_after_seconds) == (12, 30)
    assert (row.rate_limit_reset, row.rate_limit_remaining) == (reset, 0)
    assert {c.name for c in SourceCall.__table__.columns} == {
        "id", "source", "mode", "called_at", "http_status", "result_status", "reason",
        "duration_ms", "retry_after_seconds", "rate_limit_reset", "rate_limit_remaining",
    }  # fmt: skip


def test_adapter_yang_melempar_exception_meninggalkan_reservasi_yang_tetap_dihitung(
    engine,
):
    clock = Clock()

    def boom(ip):
        raise RuntimeError("berisi-rahasia")

    gateway = make_gateway(
        FakeSource(V, boom), engine, clock=clock, policy=QuotaPolicy(per_minute=1)
    )

    with pytest.raises(RuntimeError):
        gateway.fetch("8.8.8.8")

    (row,) = calls_in(engine)
    assert row.result_status is None  # tak pernah diselesaikan
    assert (
        gateway.fetch("1.1.1.1").reason is SourceReason.QUOTA_INTERNAL
    )  # tetap dihitung


# --- paralel dan lock ---------------------------------------------------------------------------------------------------


def test_10_request_paralel_tidak_menembus_batas_4_per_menit(engine):
    clock = Clock()  # jam beku: semua permintaan jatuh dalam satu jendela
    barrier = threading.Barrier(10)

    def slow(ip):
        return result_of(V, retrieved_at=clock())

    vt = FakeSource(V, slow)
    gateway = make_gateway(vt, engine, clock=clock)
    ips = [f"20.0.0.{n}" for n in range(1, 11)]

    def worker(ip):
        barrier.wait(timeout=10)
        return gateway.fetch(ip)

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(worker, ips))

    statuses = [r.status for r in results]
    assert statuses.count(SourceStatus.OK_SIGNAL) == 4
    assert statuses.count(SourceStatus.SKIPPED) == 6
    assert len(vt.calls) == 4
    assert count(engine, SourceCall, SourceCall.mode == "live") == 4


def test_lock_advisory_tidak_ditahan_selama_request_ke_sumber(engine):
    clock = Clock()
    observed = {}

    def fetch_while_checking_lock(ip):
        with engine.connect() as other:
            got = other.execute(
                text(
                    "SELECT pg_try_advisory_lock(hashtextextended('source_quota:virustotal', 0))"
                )
            ).scalar()
            if got:
                other.execute(
                    text(
                        "SELECT pg_advisory_unlock(hashtextextended('source_quota:virustotal', 0))"
                    )
                )
        observed["lock_free"] = got
        return result_of(V, retrieved_at=clock())

    gateway = make_gateway(
        FakeSource(V, fetch_while_checking_lock), engine, clock=clock
    )

    gateway.fetch("8.8.8.8")

    assert observed == {"lock_free": True}


def test_lock_per_sumber_tidak_saling_memblokir(engine):
    clock = Clock()
    held = {}

    def check_other_source_lock(ip):
        with engine.connect() as other:
            held["abuseipdb"] = other.execute(
                text(
                    "SELECT pg_try_advisory_lock(hashtextextended('source_quota:abuseipdb', 0))"
                )
            ).scalar()
            other.execute(
                text(
                    "SELECT pg_advisory_unlock(hashtextextended('source_quota:abuseipdb', 0))"
                )
            )
        return result_of(V, retrieved_at=clock())

    make_gateway(FakeSource(V, check_other_source_lock), engine, clock=clock).fetch(
        "8.8.8.8"
    )

    assert held == {"abuseipdb": True}
