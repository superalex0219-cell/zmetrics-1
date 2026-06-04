from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])
settings = get_settings()

_redis_client: Redis | None = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict:
    db_status = "ok"
    cache_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis = get_redis()
        await redis.ping()
    except Exception:
        cache_status = "error"

    overall = "ok" if db_status == "ok" and cache_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "cache": cache_status}


@router.get("/health/ready")
async def readiness() -> dict:
    return {"status": "ready"}
