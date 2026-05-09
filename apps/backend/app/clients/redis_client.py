from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis | None:
    global _redis
    redis_url = get_settings().redis_url
    if not redis_url:
        return None
    if _redis is None:
        _redis = Redis.from_url(redis_url, decode_responses=True)
    return _redis


async def ping_redis() -> bool:
    client = get_redis()
    if client is None:
        return False
    return bool(await client.ping())
