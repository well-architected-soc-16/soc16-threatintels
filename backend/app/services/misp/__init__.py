from app.core.config import get_settings
from app.services.misp.base import MispClient, SubmissionResult
from app.services.misp.live import LiveMispClient
from app.services.misp.mock import MockMispClient

__all__ = ["MispClient", "SubmissionResult", "get_misp_client"]


def get_misp_client() -> MispClient:
    """Factory berdasarkan MISP_MODE. Dipakai sebagai dependency FastAPI."""
    if get_settings().misp_mode == "live":
        return LiveMispClient()
    return MockMispClient()
