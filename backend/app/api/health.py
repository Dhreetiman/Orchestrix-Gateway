from fastapi import APIRouter, status
from sqlalchemy import text

from app.cache.redis_client import get_redis
from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    """Liveness: process is up. No external deps checked."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness() -> dict[str, object]:
    """Readiness: confirms Postgres + Redis are reachable."""
    checks: dict[str, str] = {}
    overall_ok = True

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc!s}"
        overall_ok = False

    try:
        pong = await get_redis().ping()
        checks["redis"] = "ok" if pong else "error: no pong"
        if not pong:
            overall_ok = False
    except Exception as exc:
        checks["redis"] = f"error: {exc!s}"
        overall_ok = False

    return {"status": "ok" if overall_ok else "degraded", "checks": checks}
