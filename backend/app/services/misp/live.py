from app.services.misp.base import SubmissionResult


class LiveMispClient:
    """Klien MISP asli (akan memakai PyMISP). Belum diimplementasikan.

    Saat diisi nanti: URL dan API key MISP dari konfigurasi, verifikasi TLS
    memakai file CA (bukan dimatikan), dan tidak ada rahasia di log.
    """

    def submit_indicator(
        self, ip: str, reason: str, tags: list[str], submitted_by: str
    ) -> SubmissionResult:
        raise NotImplementedError(
            "MISP_MODE=live belum diimplementasikan; gunakan MISP_MODE=mock"
        )
