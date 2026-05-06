import os

import asyncpg
import redis


def _postgres_dsn() -> str:
    return os.getenv("DB_URL", "").replace("+asyncpg", "")


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "")


async def check_dependencies() -> dict[str, str]:
    results: dict[str, str] = {}

    try:
        db_url = _postgres_dsn()
        if not db_url:
            raise RuntimeError("DB_URL is not set")
        conn = await asyncpg.connect(db_url)
        await conn.fetchval("SELECT 1")
        await conn.close()
        results["db"] = "ok"
    except Exception as exc:
        results["db"] = f"error: {exc}"

    try:
        redis_url = _redis_url()
        if not redis_url:
            raise RuntimeError("REDIS_URL is not set")
        client = redis.from_url(redis_url)
        client.ping()
        results["redis"] = "ok"
    except Exception as exc:
        results["redis"] = f"error: {exc}"

    return results
