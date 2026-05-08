from redis.asyncio import Redis

from app.settings import get_settings

_cache: Redis | None = None


async def get_cache() -> Redis:
    global _cache
    if _cache is None:
        _cache = Redis.from_url(get_settings().redis_dsn, decode_responses=True)
    return _cache


async def cache_ping() -> bool:
    cache = await get_cache()
    return bool(await cache.ping())


async def close_cache() -> None:
    global _cache
    if _cache is not None:
        await _cache.aclose()
        _cache = None

