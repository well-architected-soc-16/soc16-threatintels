import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.routers import admin, auth, checks, health, iocs
from app.services.sources.factory import close_http_client

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    close_http_client()


app = FastAPI(title="SOC16 Threat Intel Aggregator", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(checks.router, prefix="/api/v1")
app.include_router(iocs.router, prefix="/api/v1")

logging.getLogger(__name__).info(
    "aplikasi dimulai env=%s misp_mode=%s sources_mode=%s",
    settings.app_env,
    settings.misp_mode,
    settings.sources_mode,
)
