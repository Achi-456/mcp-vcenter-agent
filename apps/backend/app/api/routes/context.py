from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.vcenter_client_factory import with_vcenter
from app.services.vcenter_inventory_service import (
    context_environment,
    context_powered_off_vms,
    context_datastore_health,
    context_active_alarms,
    context_recent_events,
    context_rke2_vms,
)
from app.services.inventory_cache_service import get_cache, set_cache
from app.core.inventory_errors import error_response

router = APIRouter(prefix="/api/v1/context")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_and_cache(key: str, fetcher, ttl: int = 30):
    async def handler():
        cached = await get_cache(key)
        if cached:
            import json
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)

        result = with_vcenter(fetcher)
        if isinstance(result, dict) and "error_code" in result:
            return JSONResponse(result, status_code=409)

        data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
        await set_cache(key, data, ttl)
        return JSONResponse(data)
    return handler


@router.get("/environment")
async def environment():
    return await _fetch_and_cache("context:environment", context_environment, ttl=15)()


@router.get("/powered-off-vms")
async def powered_off_vms():
    return await _fetch_and_cache("context:powered-off-vms", context_powered_off_vms, ttl=30)()


@router.get("/datastore-health")
async def datastore_health():
    return await _fetch_and_cache("context:datastore-health", context_datastore_health, ttl=60)()


@router.get("/active-alarms")
async def active_alarms():
    return await _fetch_and_cache("context:active-alarms", context_active_alarms, ttl=30)()


@router.get("/recent-events")
async def recent_events():
    return await _fetch_and_cache("context:recent-events", context_recent_events, ttl=30)()


@router.get("/rke2-vms")
async def rke2_vms():
    return await _fetch_and_cache("context:rke2-vms", context_rke2_vms, ttl=30)()
