from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from app.tools.cache import cache_get, cache_set, should_cache as cache_should_cache
from app.tools.mcp_client import execute_tool_via_mcp
from app.tools.schemas import RiskLevel, ToolSpec
from app.tools.vcenter_tools import get_all_tool_specs, get_executor

logger = structlog.get_logger()

FASTAPI_INTERNAL = os.getenv(
    "FASTAPI_INTERNAL_URL",
    "http://fastapi.agentic-app.svc.cluster.local:8000",
)

# ── Legacy ToolDef (backward compat) ────────────────────────────────────────


@dataclass
class ToolDef:
    name: str
    description: str
    risk: str
    category: str
    api_endpoint: str
    requires_approval: bool = False


# Legacy tools list (keep for backward compat)
TOOLS: list[ToolDef] = [
    ToolDef(name="get_environment_overview", description="Get complete vCenter environment overview.", risk="read_only", category="context", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/environment"),
    ToolDef(name="list_vms", description="List all virtual machines.", risk="read_only", category="inventory", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/vms"),
    ToolDef(name="list_hosts", description="List all ESXi hosts.", risk="read_only", category="inventory", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/hosts"),
    ToolDef(name="list_clusters", description="List all vSphere clusters.", risk="read_only", category="inventory", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/clusters"),
    ToolDef(name="list_datastores", description="List all datastores.", risk="read_only", category="inventory", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/datastores"),
    ToolDef(name="list_networks", description="List all networks and port groups.", risk="read_only", category="inventory", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/networks"),
    ToolDef(name="get_powered_off_vms", description="Get powered-off VMs.", risk="read_only", category="context", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/powered-off-vms"),
    ToolDef(name="get_datastore_health", description="Analyze datastore health.", risk="read_only", category="context", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/datastore-health"),
    ToolDef(name="get_active_alarms", description="List active alarms.", risk="read_only", category="monitoring", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/active-alarms"),
    ToolDef(name="get_recent_events", description="List recent vCenter events.", risk="read_only", category="monitoring", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/recent-events"),
    ToolDef(name="get_rke2_vms", description="Find RKE2 cluster VMs.", risk="read_only", category="context", api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/rke2-vms"),
]


def get_tool(name: str) -> ToolDef | None:
    for t in TOOLS:
        if t.name == name:
            return t
    return None


def get_tools_by_category(category: str) -> list[ToolDef]:
    return [t for t in TOOLS if t.category == category]


def get_all_tools() -> list[ToolDef]:
    return list(TOOLS)


# ── New ToolSpec registry ───────────────────────────────────────────────────


@dataclass
class RegisteredTool:
    spec: ToolSpec
    executor: Callable[[dict], Any] | None


_registry: dict[str, RegisteredTool] = {}


def register_tool(spec: ToolSpec, executor: Callable | None = None) -> None:
    if spec.name in _registry:
        logger.warning("tool_already_registered", tool=spec.name, action="overwriting")
    _registry[spec.name] = RegisteredTool(spec=spec, executor=executor)


def get_tool_spec(name: str) -> RegisteredTool | None:
    return _registry.get(name)


def list_tools(include_disabled: bool = True) -> list[RegisteredTool]:
    if include_disabled:
        return list(_registry.values())
    return [t for t in _registry.values() if t.spec.enabled and t.spec.implemented]


def get_enabled_tools() -> list[RegisteredTool]:
    return [t for t in _registry.values() if t.spec.enabled and t.spec.implemented and t.spec.risk_level == RiskLevel.READ_ONLY]


# ── Build registry from vcenter_tools specs ─────────────────────────────────


def _build_registry() -> None:
    for spec in get_all_tool_specs():
        executor = get_executor(spec)
        register_tool(spec, executor)


_build_registry()


# ── Execute tool ────────────────────────────────────────────────────────────


async def execute_tool(name: str, args: dict, *, run_id: str | None = None) -> dict:
    registered = get_tool_spec(name)

    # Fallback to MCP for tools not in new registry
    if not registered:
        mcp_result = await execute_tool_via_mcp(name, args)
        mcp_result["tool"] = name
        if mcp_result.get("status") != "error" and mcp_result.get("ok") is not False:
            mcp_result["ok"] = True
        else:
            mcp_result["ok"] = False
        mcp_result["cached"] = False
        return mcp_result

    spec = registered.spec

    if not spec.enabled:
        return {"ok": False, "error_code": "TOOL_DISABLED", "tool": name, "message": f"Tool '{name}' is disabled in this phase.", "risk_level": spec.risk_level.value}

    if not spec.implemented:
        return {"ok": False, "error_code": "TOOL_NOT_IMPLEMENTED", "tool": name, "message": f"Tool '{name}' is not yet implemented.", "risk_level": spec.risk_level.value}

    if spec.risk_level != RiskLevel.READ_ONLY:
        return {"ok": False, "error_code": "TOOL_REQUIRES_APPROVAL", "tool": name, "message": f"Tool '{name}' requires approval and is disabled in Fix 5. Only read-only tools are available.", "risk_level": spec.risk_level.value}

    if registered.executor is None:
        return {"ok": False, "error_code": "TOOL_NO_EXECUTOR", "tool": name, "message": f"Tool '{name}' has no executor registered."}

    refresh = bool(args.get("refresh", False))

    if not refresh:
        cached = await cache_get(name, args)
        if cached is not None:
            cached["cached"] = True
            cached["tool"] = name
            return cached

    try:
        result = await registered.executor(spec, args)
    except Exception as exc:
        logger.error("tool_execution_failed", tool=name, error=str(exc)[:200])
        return {"ok": False, "error_code": "TOOL_EXECUTION_ERROR", "tool": name, "message": str(exc)[:200]}

    if not isinstance(result, dict):
        return {"ok": False, "error_code": "TOOL_INVALID_RESULT", "tool": name, "message": "Tool returned non-dict result."}

    result["tool"] = name

    if cache_should_cache(spec.risk_level.value, result):
        await cache_set(name, args, result, ttl=spec.cache_ttl_seconds)

    result["cached"] = False
    return result
