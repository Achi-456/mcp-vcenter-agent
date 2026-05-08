import json
import os

import redis.asyncio as redis


_redis_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "")
        if not url:
            raise RuntimeError("REDIS_URL not configured")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


async def get_cache(key: str) -> str | None:
    try:
        return await _redis().get(key)
    except Exception:
        return None


async def set_cache(key: str, value: dict, ttl: int = 30) -> None:
    try:
        await _redis().setex(key, ttl, json.dumps(value))
    except Exception:
        pass


async def clear_cache(pattern: str = "inventory:*") -> None:
    try:
        keys = await _redis().keys(pattern)
        if keys:
            await _redis().delete(*keys)
    except Exception:
        pass
