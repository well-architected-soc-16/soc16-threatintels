"""Logger pustaka HTTP tidak boleh mencetak URL atau header request (TASK-02 Tahap 0).

httpx mencatat `HTTP Request: GET <url> ...` pada level INFO. Adapter sumber nanti memakai
URL yang memuat IP yang dicek, jadi level logger httpx/httpcore dipaku di WARNING.
"""

import logging

import httpx
import pytest

from app.core.logging import setup_logging

API_KEY = "KEY-UJI-RAHASIA-0123456789abcdef"
HTTP_LOGGERS = ("httpx", "httpcore")


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def restore_logging():
    """`setup_logging` mengubah logger global; kembalikan agar test lain tidak terpengaruh."""
    names = ["", "uvicorn", "uvicorn.error", "uvicorn.access", *HTTP_LOGGERS]
    saved = {
        name: (
            logging.getLogger(name).handlers[:],
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
            logging.getLogger(name).disabled,
        )
        for name in names
    }
    yield
    for name, (handlers, level, propagate, disabled) in saved.items():
        lg = logging.getLogger(name)
        lg.handlers = handlers
        lg.setLevel(level)
        lg.propagate = propagate
        lg.disabled = disabled


@pytest.mark.parametrize("app_level", ["INFO", "DEBUG", "WARNING"])
@pytest.mark.parametrize("name", HTTP_LOGGERS)
def test_logger_http_selalu_warning_apa_pun_log_level_aplikasi(
    restore_logging, app_level, name
):
    setup_logging(app_level)

    assert logging.getLogger(name).level == logging.WARNING
    assert not logging.getLogger(name).isEnabledFor(logging.INFO)


@pytest.mark.parametrize("app_level", ["INFO", "DEBUG"])
def test_request_httpx_tidak_menghasilkan_log_url_maupun_key(
    restore_logging, app_level
):
    setup_logging(app_level)
    handler = _ListHandler()
    logging.getLogger().addHandler(handler)

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        resp = client.get(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": "8.8.8.8"},
            headers={"Key": API_KEY},
        )

    assert resp.status_code == 200
    joined = "\n".join(handler.messages)
    assert "abuseipdb" not in joined
    assert "8.8.8.8" not in joined
    assert "KEY-UJI-RAHASIA" not in joined


def test_kontrol_tanpa_setup_logging_httpx_memang_mencatat_url(restore_logging):
    # Menjaga test di atas bermakna: tanpa pengaturan level, pesan itu memang muncul.
    for name in HTTP_LOGGERS:
        logging.getLogger(name).setLevel(logging.NOTSET)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = _ListHandler()
    root.addHandler(handler)

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    try:
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            client.get("https://api.abuseipdb.com/api/v2/check?ipAddress=8.8.8.8")
    finally:
        root.removeHandler(handler)

    assert any("8.8.8.8" in m for m in handler.messages)
