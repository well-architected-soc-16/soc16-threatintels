import logging
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def check_db() -> bool:
    # OSError: file password DB tidak terbaca saat engine dibuat.
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError) as exc:
        # Hanya nama kelas error; pesan driver bisa memuat detail koneksi.
        logger.warning("cek database gagal: %s", type(exc).__name__)
        return False
