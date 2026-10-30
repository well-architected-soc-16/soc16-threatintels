"""Guard MISP untuk hasil simulasi (TASK-02 Tahap 2, Keputusan 10).

Cek ber-flag `SUMBER_SIMULASI` tidak boleh dikirim: 422, tanpa baris submission (bahkan bukan
`pending`), tanpa memanggil klien MISP, dan tanpa audit `ioc_submit*`. Cek tanpa flag itu tetap
bisa dikirim (kontrol positif).
"""

import pytest
from sqlalchemy import func, select

from app.main import app
from app.models import AuditLog, IocSubmission, Role
from app.services.misp import get_misp_client
from app.services.sources.factory import get_sources
from tests.sources_support import (
    NYATA_ABUSEIPDB,
    NYATA_VIRUSTOTAL,
    live_adapters,
    post,
    reply,
)

MISP = "/api/v1/iocs/misp"
REASON = "Terlihat melakukan brute force SSH berulang ke soc-ir"


class SpyMisp:
    def __init__(self):
        self.calls: list[tuple] = []

    def submit_indicator(self, ip, reason, tags, submitted_by):
        from app.services.misp import SubmissionResult

        self.calls.append((ip, reason, tags, submitted_by))
        return SubmissionResult(status="mock_sent", misp_event_uuid="MOCK-spy")


@pytest.fixture
def spy_misp():
    spy = SpyMisp()
    app.dependency_overrides[get_misp_client] = lambda: spy
    yield spy
    app.dependency_overrides.pop(get_misp_client, None)
    app.dependency_overrides.pop(get_sources, None)


def send(client, login, check_id: int, user: str = "misp"):
    return client.post(
        MISP, json={"check_id": check_id, "reason": REASON}, headers=login(user)
    )


def assert_nothing_sent(db, spy: SpyMisp) -> None:
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(IocSubmission)) == 0
    assert spy.calls == []
    actions = list(db.scalars(select(AuditLog.action)))
    assert not [a for a in actions if a.startswith("ioc_submit")]


@pytest.fixture
def users(make_user):
    make_user("analyst", Role.ANALYST)
    make_user("misp", Role.ANALYST, can_send_misp=True)
    make_user("boss", Role.ADMIN)


@pytest.mark.parametrize(
    "ip", ["1.1.1.1", "8.8.4.4", "8.8.8.8", "9.9.9.9", "208.67.222.222"]
)
def test_cek_simulasi_dari_api_ditolak_422_tanpa_jejak(
    client, users, login, db, spy_misp, ip
):
    # 8.8.4.4 sengaja ikut: kedua sumbernya tidak bisa dinilai, tetapi tetap simulasi.
    check = post(client, login, ip).json()
    assert "SUMBER_SIMULASI" in check["flags"]

    resp = send(client, login, check["id"])

    assert resp.status_code == 422
    assert "SUMBER_SIMULASI" in resp.json()["detail"]
    assert_nothing_sent(db, spy_misp)


def test_admin_juga_tidak_bisa_mengirim_cek_simulasi(
    client, users, login, db, spy_misp
):
    check = post(client, login, "1.1.1.1").json()

    resp = send(client, login, check["id"], user="boss")

    assert resp.status_code == 422
    assert_nothing_sent(db, spy_misp)


def test_retry_berulang_atas_cek_simulasi_tetap_422(client, users, login, db, spy_misp):
    check = post(client, login, "1.1.1.1").json()

    first = send(client, login, check["id"])
    second = send(client, login, check["id"])

    assert (first.status_code, second.status_code) == (422, 422)
    assert_nothing_sent(db, spy_misp)


def test_izin_misp_tetap_dicek_lebih_dulu_403_bukan_422(
    client, users, login, db, spy_misp
):
    check = post(client, login, "1.1.1.1").json()

    resp = send(client, login, check["id"], user="analyst")  # tanpa can_send_misp

    assert resp.status_code == 403
    assert_nothing_sent(db, spy_misp)


@pytest.mark.parametrize(
    "flags",
    [
        ["SUMBER_SIMULASI"],
        ["WHITELISTED", "SUMBER_SIMULASI"],
        ["HASIL_BERBEDA", "NO_VENDOR_OPINION", "SUMBER_SIMULASI"],
    ],
)
def test_flag_simulasi_di_antara_flag_lain_tetap_ditolak(
    client, users, make_check, login, db, spy_misp, flags
):
    check = make_check("8.8.8.8", "COMPLETE", coverage="2/2", flags=flags)

    resp = send(client, login, check.id)

    assert resp.status_code == 422
    assert_nothing_sent(db, spy_misp)


# --- kontrol positif: cek tanpa SUMBER_SIMULASI tetap bisa dikirim -------------------------


@pytest.mark.parametrize(
    "flags", [[], ["HASIL_BERBEDA"], ["WHITELISTED", "NO_VENDOR_OPINION"]]
)
def test_cek_tanpa_flag_simulasi_tetap_bisa_dikirim(
    client, users, make_check, login, db, spy_misp, flags
):
    check = make_check("8.8.8.8", "COMPLETE", coverage="2/2", flags=flags)

    resp = send(client, login, check.id)

    assert resp.status_code == 201
    assert resp.json()["status"] == "mock_sent"
    assert len(spy_misp.calls) == 1


def test_cek_data_nyata_lewat_api_bisa_dikirim_ke_misp(
    client, users, login, db, spy_misp
):
    app.dependency_overrides[get_sources] = lambda: live_adapters(
        reply(200, fixture=NYATA_ABUSEIPDB), reply(200, fixture=NYATA_VIRUSTOTAL)
    )
    check = post(client, login, "118.25.6.39").json()
    assert check["flags"] == []

    resp = send(client, login, check["id"])

    assert resp.status_code == 201
    assert spy_misp.calls[0][0] == "118.25.6.39"
