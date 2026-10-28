import uuid

from app.services.misp.base import SubmissionResult


class MockMispClient:
    """Pengganti MISP selama MISP belum terpasang. Tidak menghubungi apa pun."""

    def submit_indicator(
        self, ip: str, reason: str, tags: list[str], submitted_by: str
    ) -> SubmissionResult:
        return SubmissionResult(
            status="mock_sent", misp_event_uuid=f"MOCK-{uuid.uuid4()}"
        )
