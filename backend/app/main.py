from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import engine
from app.routers import admin, analysis, analysis_results, blast_events, capture_sessions, devices, health, me, passports, quarries, reports

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("zmetrics_backend_starting", version="0.1.0")
    yield
    await engine.dispose()
    logger.info("zmetrics_backend_stopped")


app = FastAPI(
    title="ZMetrics API",
    description="Quarry blast fragmentation analysis platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health (no auth)
app.include_router(health.router)

app.include_router(me.router, prefix="/api/v1/me", tags=["me"])

# Core API
app.include_router(quarries.router, prefix="/api/v1/quarries", tags=["quarries"])
app.include_router(
    passports.router,
    prefix="/api/v1/quarries/{quarry_id}/passports",
    tags=["passports"],
)
app.include_router(
    analysis.router,
    prefix="/api/v1/captures",
    tags=["analysis"],
)
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(
    analysis_results.router,
    prefix="/api/v1/analysis-results",
    tags=["analysis-results"],
)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(
    blast_events.router,
    prefix="/api/v1/quarries/{quarry_id}/passports/{passport_id}",
    tags=["blast-events"],
)
app.include_router(
    capture_sessions.router,
    prefix="/api/v1/capture-sessions",
    tags=["capture-sessions"],
)
