import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models import AuditLog, IocSubmission, Role
from app.routers import iocs as iocs_router
from app.services.misp import SubmissionResult, get_misp_client
from app.services.misp.live import LiveMispClient
from app.services.misp.mock import MockMispClient

IOCS = "/api/v1/iocs"
MISP = f"{IOCS}/misp"
REASON = "Terlihat melakukan brute force SSH berulang ke soc-ir"


def _submissions(db) -> list[IocSubmission]:
    db.expire_all()
    return list(db.scalars(select(IocSubmission).order_by(IocSubmission.id)))


def _body(check_id: int, **extra) -> dict:
    return {"check_id": check_id, "reason": REASON, **extra}


class FailingClient:
    """Klien MISP yang gagal dan pesan exception-nya memuat rahasia."""

    def submit_indicator(self, ip, reason, tags, submitted_by):
        raise ConnectionError("https://misp.lab/?apikey=RAHASIA-API-KEY ditolak")


class ReturnsFailedClient:
    def submit_indicator(self, ip, reason, tags, submitted_by):
        return SubmissionResult(status="failed", error_message="MISP menolak: 503")


class FlakyThenOkClient:
    def __init__(self):
        self.calls = 0

    def submit_indicator(self, ip, reason, tags, submitted_by):
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("timeout")
        return SubmissionResult(status="mock_sent", misp_event_uuid="MOCK-retry")


@pytest.fixture
def use_client():
    def _use(client_obj):
        app.dependency_overrides[get_misp_client] = lambda: client_obj

    yield _use
    app.dependency_overrides.pop(get_misp_client, None)


# --- RBAC ----------------------------------------------------------------


def test_analyst_tanpa_izin_misp_403(client, make_user, make_check, login, db):
    make_user("analyst", Role.ANALYST)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("analyst"))

    assert resp.status_code == 403
    assert _submissions(db) == []


def test_viewer_403_walau_flag_misp_true(client, make_user, make_check, login, db):
    make_user("viewer", Role.VIEWER, can_send_misp=True)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("viewer"))

    assert resp.status_code == 403
    assert _submissions(db) == []


def test_penolakan_403_tidak_memanggil_klien_misp(
    client, make_user, make_check, login, use_client
):
    class Spy:
        calls = 0

        def submit_indicator(self, *args):
            Spy.calls += 1

    use_client(Spy())
    make_user("analyst", Role.ANALYST)
    check = make_check()

    client.post(MISP, json=_body(check.id), headers=login("analyst"))

    assert Spy.calls == 0


def test_tanpa_token_401(client):
    assert client.post(MISP, json={"check_id": 1, "reason": REASON}).status_code == 401
    assert client.get(IOCS).status_code == 401


def test_penolakan_403_tercatat_di_audit(client, make_user, make_check, login, db):
    make_user("analyst", Role.ANALYST)
    check = make_check()

    client.post(MISP, json=_body(check.id), headers=login("analyst"))

    db.expire_all()
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "access_denied")).one()
    assert entry.actor_username == "analyst"
    assert entry.target == f"POST {MISP}"


# --- Pengiriman sukses (mock) ---------------------------------------------


def test_analyst_misp_kirim_201_mock_sent(client, make_user, make_check, login, db):
    make_user("analyst_misp", Role.ANALYST, can_send_misp=True)
    check = make_check("8.8.8.8")

    resp = client.post(
        MISP,
        json=_body(check.id, tags=["ssh-bruteforce"]),
        headers=login("analyst_misp"),
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "mock_sent"
    assert body["misp_event_uuid"].startswith("MOCK-")
    assert body["error_message"] is None
    assert body["check_id"] == check.id
    assert body["ip"] == "8.8.8.8"  # diambil dari check, bukan dari request
    assert body["tags"] == ["ssh-bruteforce"]
    assert body["submitted_by"] == "analyst_misp"
    assert body["submitted_at"].endswith("+07:00")
    assert len(_submissions(db)) == 1


def test_admin_boleh_kirim(client, make_user, make_check, login):
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 201
    assert resp.json()["tags"] == []


def test_alasan_di_trim_dan_pengiriman_tercatat_di_audit(
    client, make_user, make_check, login, db
):
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(
        MISP,
        json={"check_id": check.id, "reason": f"  {REASON}  "},
        headers=login("boss"),
    )

    assert resp.json()["reason"] == REASON
    db.expire_all()
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "ioc_submit")).one()
    assert (entry.result, entry.actor_username, entry.target) == (
        "success",
        "boss",
        "8.8.8.8",
    )
    assert entry.detail["status"] == "mock_sent"
    assert REASON not in str(entry.detail)


def test_mock_tidak_membuka_koneksi_keluar(
    client, make_user, make_check, login, monkeypatch
):
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")

    def fail_network(*args, **kwargs):
        raise AssertionError("mock MISP tidak boleh menghubungi jaringan")

    monkeypatch.setattr(socket.socket, "connect", fail_network)
    monkeypatch.setattr(socket, "getaddrinfo", fail_network)

    resp = client.post(MISP, json=_body(check.id), headers=headers)

    assert resp.status_code == 201


# --- Anti-duplikat ---------------------------------------------------------


def test_kirim_dua_kali_409_berisi_id_yang_ada(
    client, make_user, make_check, login, db
):
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    first = client.post(MISP, json=_body(check.id), headers=headers)

    second = client.post(MISP, json=_body(check.id), headers=headers)

    assert second.status_code == 409
    assert second.json()["submission_id"] == first.json()["id"]
    assert len(_submissions(db)) == 1


def test_duplikat_dari_user_lain_tetap_409(client, make_user, make_check, login, db):
    make_user("boss", Role.ADMIN)
    make_user("analyst_misp", Role.ANALYST, can_send_misp=True)
    check = make_check()
    first = client.post(MISP, json=_body(check.id), headers=login("boss"))

    second = client.post(MISP, json=_body(check.id), headers=login("analyst_misp"))

    assert second.status_code == 409
    assert second.json()["submission_id"] == first.json()["id"]
    assert len(_submissions(db)) == 1


def test_duplikat_tidak_memanggil_klien_lagi(
    client, make_user, make_check, login, use_client
):
    calls = []

    class Counting(MockMispClient):
        def submit_indicator(self, *args):
            calls.append(args)
            return super().submit_indicator(*args)

    use_client(Counting())
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")

    client.post(MISP, json=_body(check.id), headers=headers)
    client.post(MISP, json=_body(check.id), headers=headers)

    assert len(calls) == 1


def test_race_dua_request_bersamaan_tetap_satu_baris(
    client, make_user, make_check, login, db, monkeypatch
):
    """Request kedua lolos pengecekan awal (belum melihat baris pertama), tetapi
    UNIQUE(check_id) menolak INSERT-nya dan hasilnya tetap 409."""
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    first = client.post(MISP, json=_body(check.id), headers=headers)
    monkeypatch.setattr(
        iocs_router, "_find_existing", _blind_once(iocs_router._find_existing)
    )

    second = client.post(MISP, json=_body(check.id), headers=headers)

    assert second.status_code == 409
    assert second.json()["submission_id"] == first.json()["id"]
    assert len(_submissions(db)) == 1


def _blind_once(real):
    state = {"first": True}

    def wrapper(db, check_id):
        if state["first"]:
            state["first"] = False
            return None
        return real(db, check_id)

    return wrapper


def test_duplikat_tercatat_di_audit(client, make_user, make_check, login, db):
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    client.post(MISP, json=_body(check.id), headers=headers)
    client.post(MISP, json=_body(check.id), headers=headers)

    db.expire_all()
    entry = db.scalars(
        select(AuditLog).where(AuditLog.action == "ioc_submit_duplicate")
    ).one()
    assert entry.result == "denied"
    assert entry.detail["check_id"] == check.id


# --- Validasi --------------------------------------------------------------


@pytest.mark.parametrize(
    "reason", ["", "   ", "pendek", "123456789", "         x         "]
)
def test_alasan_kosong_atau_kurang_dari_10_karakter_422(
    client, make_user, make_check, login, db, reason
):
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(
        MISP, json={"check_id": check.id, "reason": reason}, headers=login("boss")
    )

    assert resp.status_code == 422
    assert _submissions(db) == []


def test_alasan_tidak_ada_422(client, make_user, make_check, login):
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json={"check_id": check.id}, headers=login("boss"))

    assert resp.status_code == 422


@pytest.mark.parametrize(
    "tags", [[""], ["x" * 65], [f"t{i}" for i in range(21)], "bukan-list", [1]]
)
def test_tags_tidak_valid_422(client, make_user, make_check, login, tags):
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id, tags=tags), headers=login("boss"))

    assert resp.status_code == 422


def test_check_tidak_ada_404(client, make_user, login, db):
    make_user("boss", Role.ADMIN)

    resp = client.post(MISP, json=_body(9999), headers=login("boss"))

    assert resp.status_code == 404
    assert _submissions(db) == []


def test_check_input_ditolak_tidak_boleh_dikirim_422(
    client, make_user, make_check, login, db, use_client
):
    calls = []

    class Spy:
        def submit_indicator(self, *args):
            calls.append(args)

    use_client(Spy())
    make_user("boss", Role.ADMIN)
    check = make_check(assessment_status="INPUT_DITOLAK")

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 422
    assert "input ditolak" in resp.json()["detail"]
    assert _submissions(db) == []  # tidak ada baris, bahkan bukan `pending`
    assert calls == []  # klien MISP tidak dipanggil
    db.expire_all()
    actions = {a.action for a in db.scalars(select(AuditLog))}
    assert not actions & {"ioc_submit", "ioc_submit_retry"}


@pytest.mark.parametrize("ip", ["10.0.0.5", "abc", "::1"])
def test_input_ditolak_dari_api_tidak_pernah_menjadi_check_yang_bisa_dikirim(
    client, make_user, login, db, ip
):
    """Jalur nyata: POST /checks yang ditolak tidak menyimpan check, jadi tidak ada
    check_id yang bisa dipakai untuk mengirim ke MISP."""
    make_user("boss", Role.ADMIN)
    headers = login("boss")

    rejected = client.post("/api/v1/checks", json={"ip": ip}, headers=headers)
    listing = client.get("/api/v1/checks", headers=headers).json()
    submit = client.post(MISP, json=_body(1), headers=headers)

    assert rejected.status_code == 422
    assert listing["total"] == 0
    assert submit.status_code == 404
    assert _submissions(db) == []


# --- Kegagalan tidak boleh tampil sebagai sukses ---------------------------


def test_klien_gagal_disimpan_failed_502_tanpa_membocorkan_rahasia(
    client, make_user, make_check, login, db, use_client
):
    use_client(FailingClient())
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 502
    body = resp.json()
    assert body["status"] == "failed"
    assert body["misp_event_uuid"] is None
    assert "RAHASIA-API-KEY" not in resp.text
    assert "ConnectionError" in body["error_message"]
    stored = _submissions(db)
    assert [s.status for s in stored] == ["failed"]
    assert "RAHASIA-API-KEY" not in (stored[0].error_message or "")


def test_klien_mengembalikan_failed_juga_502(
    client, make_user, make_check, login, use_client
):
    use_client(ReturnsFailedClient())
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 502
    assert resp.json()["status"] == "failed"
    assert resp.json()["error_message"] == "MISP menolak: 503"


def test_kegagalan_tercatat_di_audit_sebagai_error(
    client, make_user, make_check, login, db, use_client
):
    use_client(FailingClient())
    make_user("boss", Role.ADMIN)
    check = make_check()

    client.post(MISP, json=_body(check.id), headers=login("boss"))

    db.expire_all()
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "ioc_submit")).one()
    assert entry.result == "error"
    assert "RAHASIA-API-KEY" not in str(entry.detail)


def test_mode_live_belum_ada_gagal_jelas_bukan_sukses(
    client, make_user, make_check, login, db, use_client
):
    use_client(LiveMispClient())
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    # 501 (fitur belum ada), bukan 502 (gangguan di hulu) dan bukan sukses.
    assert resp.status_code == 501
    assert resp.json()["status"] == "failed"
    assert "belum diimplementasikan" in resp.json()["error_message"]
    assert [s.status for s in _submissions(db)] == ["failed"]


def test_mode_live_end_to_end_lewat_factory_dan_setting(
    client, make_user, make_check, login, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "misp_mode", "live")
    make_user("boss", Role.ADMIN)
    check = make_check()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 501


def test_retry_submission_failed_memakai_baris_yang_sama(
    client, make_user, make_check, login, db, use_client
):
    flaky = FlakyThenOkClient()
    use_client(flaky)
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    first = client.post(MISP, json=_body(check.id), headers=headers)
    assert first.status_code == 502
    failed_id = first.json()["id"]

    retry = client.post(MISP, json=_body(check.id), headers=headers)

    assert retry.status_code == 200
    assert retry.json()["id"] == failed_id
    assert retry.json()["status"] == "mock_sent"
    assert retry.json()["error_message"] is None
    assert len(_submissions(db)) == 1
    # Setelah sukses, kirim ulang kembali ditolak sebagai duplikat.
    again = client.post(MISP, json=_body(check.id), headers=headers)
    assert again.status_code == 409
    assert flaky.calls == 2


def test_setiap_retry_tercatat_di_audit(
    client, make_user, make_check, login, db, use_client
):
    use_client(FlakyThenOkClient())
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    first = client.post(MISP, json=_body(check.id), headers=headers)
    client.post(MISP, json=_body(check.id), headers=headers)  # retry

    db.expire_all()
    logs = [
        a
        for a in db.scalars(select(AuditLog).order_by(AuditLog.id))
        if a.action.startswith("ioc_submit")
    ]
    assert [(a.action, a.result, a.detail.get("retry")) for a in logs] == [
        ("ioc_submit", "error", False),  # percobaan pertama gagal
        (
            "ioc_submit_retry",
            "success",
            None,
        ),  # retry diterima (klaim failed -> pending)
        ("ioc_submit", "success", True),  # hasil retry
    ]
    retry_entry = logs[1]
    assert retry_entry.actor_username == "boss"
    assert retry_entry.detail == {
        "check_id": check.id,
        "submission_id": first.json()["id"],
        "previous_status": "failed",
    }


def test_retry_yang_kalah_klaim_tidak_tercatat_sebagai_retry(
    client, make_user, make_check, login, db, use_client
):
    """Retry setelah submission sukses ditolak 409 dan hanya tercatat sebagai duplikat."""
    use_client(FlakyThenOkClient())
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    client.post(MISP, json=_body(check.id), headers=headers)  # gagal
    client.post(MISP, json=_body(check.id), headers=headers)  # retry sukses
    late = client.post(MISP, json=_body(check.id), headers=headers)  # terlambat

    db.expire_all()
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert late.status_code == 409
    assert actions.count("ioc_submit_retry") == 1
    assert actions.count("ioc_submit_duplicate") == 1


class _SlowCountingClient:
    """Menahan pemanggilan agar jendela balapan antar-request benar-benar terbuka."""

    def __init__(self):
        self.calls = 0
        self._lock = threading.Lock()

    def submit_indicator(self, ip, reason, tags, submitted_by):
        with self._lock:
            self.calls += 1
        time.sleep(0.3)
        return SubmissionResult(status="mock_sent", misp_event_uuid="MOCK-parallel")


def _fire_parallel(headers: dict, body: dict, n: int = 10) -> list[int]:
    """Kirim n request benar-benar bersamaan (Barrier), tiap thread dengan klien sendiri."""
    barrier = threading.Barrier(n)

    def one(_):
        barrier.wait()
        return TestClient(app).post(MISP, json=body, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=n) as pool:
        return sorted(pool.map(one, range(n)))


def test_10_retry_paralel_hanya_satu_yang_lolos(
    client, make_user, make_check, login, db, use_client
):
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    use_client(FailingClient())
    assert client.post(MISP, json=_body(check.id), headers=headers).status_code == 502
    slow = _SlowCountingClient()
    use_client(slow)

    codes = _fire_parallel(headers, _body(check.id))

    assert codes == [200] + [409] * 9  # tepat satu yang lolos
    assert slow.calls == 1  # klien MISP hanya dipanggil sekali
    stored = _submissions(db)
    assert [s.status for s in stored] == ["mock_sent"]  # tetap satu baris
    db.expire_all()
    actions = [a.action for a in db.scalars(select(AuditLog))]
    assert (
        actions.count("ioc_submit_retry") == 1
    )  # hanya yang lolos tercatat sebagai retry
    assert actions.count("ioc_submit_duplicate") == 9


def test_10_pengiriman_pertama_paralel_hanya_satu_yang_lolos(
    client, make_user, make_check, login, db, use_client
):
    make_user("boss", Role.ADMIN)
    check = make_check()
    headers = login("boss")
    slow = _SlowCountingClient()
    use_client(slow)

    codes = _fire_parallel(headers, _body(check.id))

    assert codes == [201] + [409] * 9
    assert slow.calls == 1
    assert [s.status for s in _submissions(db)] == ["mock_sent"]


def test_submission_pending_dianggap_duplikat(client, make_user, make_check, login, db):
    make_user("boss", Role.ADMIN)
    check = make_check()
    db.add(
        IocSubmission(
            check_id=check.id,
            ip=check.ip,
            reason=REASON,
            tags=[],
            status="pending",
            submitted_by="boss",
        )
    )
    db.commit()

    resp = client.post(MISP, json=_body(check.id), headers=login("boss"))

    assert resp.status_code == 409


# --- GET /iocs -------------------------------------------------------------


def test_semua_role_boleh_melihat_daftar(client, make_user, make_check, login):
    make_user("boss", Role.ADMIN)
    make_user("analyst", Role.ANALYST)
    make_user("viewer", Role.VIEWER)
    check = make_check()
    client.post(MISP, json=_body(check.id), headers=login("boss"))

    for name in ("boss", "analyst", "viewer"):
        resp = client.get(IOCS, headers=login(name))
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["status"] == "mock_sent"


def test_daftar_paginasi_terbaru_dulu(client, make_user, make_check, login):
    make_user("boss", Role.ADMIN)
    headers = login("boss")
    for ip in ("8.8.8.8", "1.1.1.1", "9.9.9.9"):
        client.post(MISP, json=_body(make_check(ip).id), headers=headers)

    page1 = client.get(IOCS, params={"limit": 2}, headers=headers).json()
    page2 = client.get(IOCS, params={"limit": 2, "offset": 2}, headers=headers).json()

    assert page1["total"] == 3
    assert [i["ip"] for i in page1["items"]] == ["9.9.9.9", "1.1.1.1"]
    assert [i["ip"] for i in page2["items"]] == ["8.8.8.8"]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_daftar_parameter_tidak_valid_422(client, make_user, login, params):
    make_user("viewer", Role.VIEWER)

    assert client.get(IOCS, params=params, headers=login("viewer")).status_code == 422


# --- Factory & kontrak DB ---------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected"), [("mock", MockMispClient), ("live", LiveMispClient)]
)
def test_factory_memilih_klien_berdasarkan_misp_mode(monkeypatch, mode, expected):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "misp_mode", mode)

    assert type(get_misp_client()) is expected


def test_mock_client_mengembalikan_id_unik_berawalan_mock():
    client = MockMispClient()

    ids = {
        client.submit_indicator("8.8.8.8", REASON, [], "u").misp_event_uuid
        for _ in range(3)
    }

    assert len(ids) == 3
    assert all(i.startswith("MOCK-") for i in ids)


def test_constraint_db_menolak_alasan_pendek_dan_check_ganda(db, make_check):
    """Pertahanan berlapis: aturan juga ditegakkan di database, bukan hanya di API."""
    from sqlalchemy.exc import IntegrityError

    check = make_check()
    db.add(
        IocSubmission(
            check_id=check.id,
            ip=check.ip,
            reason="pendek",
            tags=[],
            status="pending",
            submitted_by="u",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    for _ in range(2):
        db.add(
            IocSubmission(
                check_id=check.id,
                ip=check.ip,
                reason=REASON,
                tags=[],
                status="pending",
                submitted_by="u",
            )
        )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(IocSubmission)) == 0
