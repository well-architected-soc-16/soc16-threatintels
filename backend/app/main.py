import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.routers import admin, auth, checks, health, iocs

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="SOC16 Threat Intel Aggregator", version="0.1.0")
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(checks.router, prefix="/api/v1")
app.include_router(iocs.router, prefix="/api/v1")

logging.getLogger(__name__).info(
    "aplikasi dimulai env=%s misp_mode=%s", settings.app_env, settings.misp_mode
)
