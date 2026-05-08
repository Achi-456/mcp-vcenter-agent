from __future__ import annotations

import hashlib
import json
import os

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "")
TOOL_CACHE_ENABLED = os.getenv("TOOL_CACHE_ENABLED", "true").lower() == "true"

NEVER_CACHE_TEXTS = [
    "notauthenticated",
    "session is not authenticated",
    "vcenter_auth_failed",
    "vcenter_session_expired",
    "vcenter_not_configured",
    "vcenter_unreachable",
    "nopermission",
    "invalid login",
]

_client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis | None:
    global _client
    if _client is None and REDIS_URL:
        _client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _client


def make_cache_key(tool_name: str, args: dict) -> str:
    normalized = json.dumps(args or {}, sort_keys=True, default=str)
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"tool:{tool_name}:{digest}"


def should_cache(risk_level: str, result: dict) -> bool:
    if risk_level != "read_only":
        return False
    if result.get("ok") is not True:
        return False
    if result.get("error_code"):
        return False
    if result.get("status") == "error":
        return False
    text = json.dumps(result).lower()
    for blocked in NEVER_CACHE_TEXTS:
        if blocked in text:
            return False
    return True


async def cache_get(tool_name: str, args: dict) -> dict | None:
    if not TOOL_CACHE_ENABLED:
        return None
    client = _get_client()
    if client is None:
        return None
    key = make_cache_key(tool_name, args)
    try:
        raw = await client.get(key)
        if raw is not None:
            data = json.loads(raw)
            logger.debug("tool_cache_hit", tool=tool_name, cache_key=key)
            return data
    except Exception as exc:
        logger.warning("tool_cache_get_failed", tool=tool_name, error=str(exc)[:80])
    return None


async def cache_set(tool_name: str, args: dict, result: dict, ttl: int = 30) -> None:
    if not TOOL_CACHE_ENABLED:
        return
    client = _get_client()
    if client is None:
        return
    key = make_cache_key(tool_name, args)
    try:
        await client.setex(key, ttl, json.dumps(result))
        logger.debug("tool_cache_set", tool=tool_name, cache_key=key, ttl=ttl)
    except Exception as exc:
        logger.warning("tool_cache_set_failed", tool=tool_name, error=str(exc)[:80])


async def cache_delete(tool_name: str, args: dict) -> None:
    if not TOOL_CACHE_ENABLED:
        return
    client = _get_client()
    if client is None:
        return
    key = make_cache_key(tool_name, args)
    try:
        await client.delete(key)
    except Exception:
        pass


async def cache_ping() -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        await client.ping()
        return True
    except Exception:
        return False
