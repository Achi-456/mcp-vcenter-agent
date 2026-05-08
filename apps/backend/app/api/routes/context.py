from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.vcenter_client_factory import with_vcenter
from app.services.vcenter_inventory_service import (
    context_environment,
    context_powered_off_vms,
    context_datastore_health,
    context_active_alarms,
    context_recent_events,
    context_rke2_vms,
    list_vms,
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


@router.get("/vm-details")
async def vm_details(name: str = Query(..., min_length=1)):
    def _fetch(si, content):
        vms = list_vms(si, content)
        lower = name.lower()

        # Check if name looks like a host (IP, esxi prefix)
        import re
        is_host_like = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", lower)) or lower.startswith("esxi") or lower.startswith("esx-") or lower.startswith("esx.")

        matches = [v for v in vms if lower in v["name"].lower()]
        if not matches:
            if is_host_like:
                return {
                    "ok": False,
                    "error_code": "WRONG_OBJECT_TYPE",
                    "message": f"'{name}' looks like an ESXi host, not a VM.",
                    "suggested_tool": "get_host_details",
                }
            return {
                "ok": False,
                "error_code": "VM_NOT_FOUND",
                "message": f"No VM named '{name}' was found.",
            }
        exact = [v for v in matches if v["name"].lower() == lower]
        result = exact[0] if exact else matches[0]
        return {"vms": [result], "count": 1, "summary": f"Found {result['name']}, {result['power_state']}, host {result.get('host', 'N/A')}"}

    result = with_vcenter(_fetch)
    if isinstance(result, dict) and result.get("ok") is False:
        status_code = 404 if result.get("error_code") in ("VM_NOT_FOUND", "WRONG_OBJECT_TYPE") else 409
        return JSONResponse(result, status_code=status_code)

    data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
    return JSONResponse(data)


@router.get("/host-details")
async def host_details(name: str = Query(..., min_length=1)):
    def _fetch(si, content):
        from app.services.vcenter_inventory_service import list_hosts
        hosts = list_hosts(si, content)
        lower = name.lower()
        matches = [h for h in hosts if lower in h["name"].lower()]
        if not matches:
            return {
                "ok": False,
                "error_code": "HOST_NOT_FOUND",
                "message": f"No ESXi host named '{name}' was found.",
            }
        exact = [h for h in matches if h["name"].lower() == lower]
        result = exact[0] if exact else matches[0]
        return {
            "hosts": [result],
            "count": 1,
            "summary": f"Host {result['name']} — {result.get('connection_state', 'unknown')} — {result.get('vm_count', 0)} VMs — vSphere {result.get('version', 'unknown')}",
        }

    result = with_vcenter(_fetch)
    if isinstance(result, dict) and result.get("ok") is False:
        return JSONResponse(result, status_code=404)

    data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
    return JSONResponse(data)


@router.get("/search")
async def search_inventory(q: str = Query(..., min_length=1)):
    def _fetch(si, content):
        from app.services.vcenter_inventory_service import list_hosts, list_datastores, list_networks, list_clusters
        vms = list_vms(si, content)
        hosts = list_hosts(si, content)
        datastores = list_datastores(si, content)
        networks = list_networks(si, content)
        clusters = list_clusters(si, content)
        lower = q.lower()

        matches = []
        for vm in vms:
            if lower in vm["name"].lower():
                matches.append({"type": "vm", "name": vm["name"], "confidence": 0.95})
        for host in hosts:
            if lower in host["name"].lower():
                matches.append({"type": "host", "name": host["name"], "confidence": 0.95})
        for ds in datastores:
            if lower in ds["name"].lower():
                matches.append({"type": "datastore", "name": ds["name"], "confidence": 0.95})
        for net in networks:
            if lower in net["name"].lower():
                matches.append({"type": "network", "name": net["name"], "confidence": 0.95})
        for cl in clusters:
            if lower in cl["name"].lower():
                matches.append({"type": "cluster", "name": cl["name"], "confidence": 0.95})

        return {
            "query": q,
            "matches": matches,
            "count": len(matches),
            "summary": f"Found {len(matches)} matches for '{q}'." if matches else f"No matches found for '{q}'.",
        }

    result = with_vcenter(_fetch)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
    return JSONResponse(data)
