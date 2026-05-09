import httpx

from app.clients.redis_client import ping_redis
from app.core.config import get_settings
from app.db.session import ping_postgres
from app.services.secret_store import SecretStore


class HealthService:
    async def services(self) -> dict[str, dict[str, str]]:
        settings = get_settings()
        return {
            "fastapi": {"status": "ok", "detail": "FastAPI gateway online"},
            "postgres": await self._postgres_status(),
            "redis": await self._redis_status(),
            "vcenter": await self._vcenter_status(),
            "agent_engine": await self._http_status(f"{settings.agent_engine_url}/health"),
        }

    async def _postgres_status(self) -> dict[str, str]:
        if not get_settings().db_url:
            return {"status": "not_configured", "detail": "DB_URL is not configured"}
        try:
            return (
                {"status": "ok", "detail": "Postgres reachable"}
                if await ping_postgres()
                else {"status": "degraded", "detail": "Postgres ping failed"}
            )
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc)}

    async def _redis_status(self) -> dict[str, str]:
        if not get_settings().redis_url:
            return {"status": "not_configured", "detail": "REDIS_URL is not configured"}
        try:
            return (
                {"status": "ok", "detail": "Redis reachable"}
                if await ping_redis()
                else {"status": "degraded", "detail": "Redis ping failed"}
            )
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc)}

    async def _vcenter_status(self) -> dict[str, str]:
        settings = get_settings()
        exists = await SecretStore().exists(settings.vcenter_secret_name)
        if exists:
            return {
                "status": "configured",
                "detail": f"Secret reference '{settings.vcenter_secret_name}' exists",
            }
        return {
            "status": "not_configured",
            "detail": f"Secret reference '{settings.vcenter_secret_name}' not found",
        }

    async def _http_status(self, url: str) -> dict[str, str]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(url)
            if response.is_success:
                return {"status": "ok", "detail": url}
            return {"status": "degraded", "detail": f"{url} returned {response.status_code}"}
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc)}
