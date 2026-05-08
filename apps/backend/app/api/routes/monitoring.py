import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.vcenter_client_factory import with_vcenter
from app.services.vcenter_inventory_service import list_alarms, list_events
from app.services.inventory_cache_service import get_cache, set_cache

router = APIRouter(prefix="/api/v1/monitoring")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/alarms")
async def alarms(refresh: bool = Query(False)):
    key = "monitoring:alarms"
    if not refresh:
        cached = await get_cache(key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)

    result = with_vcenter(list_alarms)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {"items": result, "count": len(result), "source": "vcenter", "cached": False, "collected_at": _now()}
    await set_cache(key, data, 60)
    return JSONResponse(data)


@router.get("/events")
async def events(refresh: bool = Query(False), limit: int = Query(50, ge=1, le=200)):
    key = "monitoring:events"
    if not refresh:
        cached = await get_cache(key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return JSONResponse(data)

    def _fetch(si, content):
        return list_events(si, content, limit)

    result = with_vcenter(_fetch)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {"items": result, "count": len(result), "source": "vcenter", "cached": False, "collected_at": _now()}
    await set_cache(key, data, 30)
    return JSONResponse(data)
