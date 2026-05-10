from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.responses import JSONResponse

from app.core.responses import error_response, success_response
from app.schemas.audit import AuditEventCreate
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService
from app.services.vcenter_session import VCenterError


TTL_SECONDS = {
    "list_vms": 60,
    "list_hosts": 60,
    "list_datastores": 60,
    "get_vm_details": 60,
    "get_host_details": 60,
    "get_datastore_health": 60,
    "get_environment_overview": 60,
    "get_rke2_vms": 60,
    "get_active_alarms": 30,
    "get_recent_events": 30,
}


def cache_key(tool_name: str, inputs: dict[str, Any] | None = None) -> str:
    if not inputs:
        return f"toolcache:{tool_name}:default"
    suffix = ":".join(f"{key}={value}" for key, value in sorted(inputs.items()))
    return f"toolcache:{tool_name}:{suffix}".lower().replace(" ", "-")


async def run_vcenter_tool(
    *,
    tool_name: str,
    operation: Callable[[], Awaitable[Any]],
    registry: ToolRegistryService,
    policy: PolicyService,
    cache: CacheService,
    audit: AuditService,
    refresh: bool = False,
    inputs: dict[str, Any] | None = None,
):
    try:
        tool = registry.get_tool(tool_name)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=error_response("TOOL_NOT_FOUND", f"Tool '{tool_name}' was not found."),
        )

    decision = policy.evaluate(tool)
    if not decision.allowed:
        await audit.record_tool_decision(
            tool_name=tool_name,
            status="blocked",
            risk_level=str(tool.risk_level),
            error_code=decision.error_code,
            metadata={"input_summary": inputs or {}},
        )
        return JSONResponse(
            status_code=403,
            content=error_response(decision.error_code or "TOOL_POLICY_BLOCKED", decision.message),
        )

    key = cache_key(tool_name, inputs)
    cached = await cache.get(key, refresh=refresh)
    if cached is not None:
        return success_response(cached, source="pyvmomi", cached=True)

    try:
        data = await operation()
    except VCenterError as exc:
        await audit.record_tool_decision(
            tool_name=tool_name,
            status="error",
            risk_level=str(tool.risk_level),
            error_code=exc.error_code,
            metadata={"input_summary": inputs or {}, "message": exc.message},
        )
        return JSONResponse(
            status_code=400,
            content=error_response(exc.error_code, exc.message, details=exc.details),
        )
    except Exception as exc:
        await audit.record_tool_decision(
            tool_name=tool_name,
            status="error",
            risk_level=str(tool.risk_level),
            error_code="VCENTER_INVENTORY_ERROR",
            metadata={"input_summary": inputs or {}, "message": str(exc)},
        )
        return JSONResponse(
            status_code=500,
            content=error_response("VCENTER_INVENTORY_ERROR", "vCenter inventory query failed."),
        )

    await cache.set(key, data, ttl_seconds=TTL_SECONDS.get(tool_name, 60))
    await audit.record_tool_decision(
        tool_name=tool_name,
        status="success",
        risk_level=str(tool.risk_level),
        metadata={"input_summary": inputs or {}, "result_type": type(data).__name__},
    )
    return success_response(data, source="pyvmomi", cached=False)
