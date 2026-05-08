import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.api.schemas.inventory import (
    InventoryListResponse, InventoryOverviewResponse,
)
from app.core.inventory_errors import error_response
from app.services.vcenter_client_factory import with_vcenter
from app.services.vcenter_inventory_service import (
    list_vms, list_hosts, list_datastores, list_networks,
    list_clusters, get_inventory_overview,
)
from app.services.inventory_cache_service import get_cache, set_cache, _redis as _cache_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/inventory")

TTL = {"vms": 30, "hosts": 30, "datastores": 60, "networks": 60, "clusters": 60, "overview": 15}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _cached_or_fetch(key: str, fetcher, ttl_key: str):
    cached = await get_cache(f"inventory:{key}")
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    result = with_vcenter(fetcher)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {"items": result, "count": len(result), "source": "vcenter", "cached": False, "collected_at": _now()}
    await set_cache(f"inventory:{key}", data, TTL.get(ttl_key, 30))
    return data


@router.get("/overview")
async def overview():
    key = "inventory:overview"
    cached = await get_cache(key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return JSONResponse(data)

    result = with_vcenter(get_inventory_overview)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
    await set_cache(key, data, TTL["overview"])
    return JSONResponse(data)


@router.get("/vms")
async def vms(refresh: bool = Query(False)):
    if not refresh:
        cached = await get_cache("inventory:vms")
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)
    return await _cached_or_fetch("vms", list_vms, "vms")


@router.get("/hosts")
async def hosts(refresh: bool = Query(False)):
    if not refresh:
        cached = await get_cache("inventory:hosts")
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)
    return await _cached_or_fetch("hosts", list_hosts, "hosts")


@router.get("/datastores")
async def datastores(refresh: bool = Query(False)):
    if not refresh:
        cached = await get_cache("inventory:datastores")
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)
    return await _cached_or_fetch("datastores", list_datastores, "datastores")


@router.get("/networks")
async def networks(refresh: bool = Query(False)):
    if not refresh:
        cached = await get_cache("inventory:networks")
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)
    return await _cached_or_fetch("networks", list_networks, "networks")


@router.get("/clusters")
async def clusters(refresh: bool = Query(False)):
    if not refresh:
        cached = await get_cache("inventory:clusters")
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)
    return await _cached_or_fetch("clusters", list_clusters, "clusters")
