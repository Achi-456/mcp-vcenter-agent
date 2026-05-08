import asyncpg
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.cache import cache_ping
from app.runtime import runtime
from app.settings import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    results: dict[str, str] = {}

    try:
        conn = await asyncpg.connect(get_settings().postgres_dsn)
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        results["db"] = "ok"
    except Exception as exc:
        results["db"] = f"error: {exc}"

    try:
        results["redis"] = "ok" if await cache_ping() else "error"
    except Exception as exc:
        results["redis"] = f"error: {exc}"

    try:
        await runtime.graph()
        results["langgraph"] = "ok"
    except Exception as exc:
        results["langgraph"] = f"error: {exc}"

    is_ready = all(value == "ok" for value in results.values())
    return JSONResponse(
        {"status": "ready" if is_ready else "degraded", **results},
        status_code=200 if is_ready else 503,
    )

