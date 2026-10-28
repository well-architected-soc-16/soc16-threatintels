from dataclasses import dataclass
from typing import Literal, Protocol

SubmissionStatus = Literal["mock_sent", "sent", "failed"]


@dataclass(frozen=True)
class SubmissionResult:
    status: SubmissionStatus
    misp_event_uuid: str | None = None
    error_message: str | None = None


class MispClient(Protocol):
    def submit_indicator(
        self, ip: str, reason: str, tags: list[str], submitted_by: str
    ) -> SubmissionResult:
        """Kirim satu indikator IP ke MISP. Kegagalan dikembalikan sebagai
        status "failed" (atau exception); tidak boleh dilaporkan sebagai sukses."""
        ...
