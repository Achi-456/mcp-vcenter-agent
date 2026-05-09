import json
from typing import Any

from app.clients.redis_client import get_redis
from app.core.errors import AUTH_FAILURE_CODES, POLICY_FAILURE_CODES


FAILED_STATUSES = {"error", "failed", "permission_denied", "not_authenticated"}


class CacheService:
    async def get(self, key: str, *, refresh: bool = False) -> Any | None:
        if refresh:
            return None
        client = get_redis()
        if client is None:
            return None
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set(self, key: str, value: Any, *, ttl_seconds: int) -> bool:
        if not self.is_cacheable(value):
            return False
        client = get_redis()
        if client is None:
            return False
        await client.set(key, json.dumps(value), ex=ttl_seconds)
        return True

    async def delete(self, key: str) -> bool:
        client = get_redis()
        if client is None:
            return False
        await client.delete(key)
        return True

    def is_cacheable(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return True

        if value.get("ok") is False:
            return False

        error_code = value.get("error_code")
        if error_code in AUTH_FAILURE_CODES or error_code in POLICY_FAILURE_CODES:
            return False

        status = str(value.get("status", "")).lower()
        if status in FAILED_STATUSES:
            return False

        message = str(value.get("message", "")).lower()
        permission_markers = ("permission", "notauthenticated", "not authenticated")
        if any(marker in message for marker in permission_markers):
            return False

        return True
