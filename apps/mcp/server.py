import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.tools.registry import (
    get_tool, get_enabled_tools, format_tool_list, ToolDef, TOOLS
)

app = FastAPI(title="vCenter MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExecuteRequest(BaseModel):
    tool: str
    arguments: dict | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    enabled = get_enabled_tools()
    return {
        "status": "ok",
        "tools": len(TOOLS),
        "enabled": len(enabled),
        "resources": [],
        "prompts": [],
    }


@app.get("/tools")
async def list_tools(category: str | None = None, enabled_only: bool = False):
    """List all registered tools, optionally filtered by category."""
    tools = get_enabled_tools() if enabled_only else TOOLS
    if category:
        tools = [t for t in tools if t.category == category]
    return {
        "tools": [t.to_dict() for t in tools],
        "categories": sorted(set(t.category for t in TOOLS)),
        "tool_list_formatted": format_tool_list(),
    }


@app.get("/tools/{name}")
async def get_tool_info(name: str):
    tool = get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return tool.to_dict()


@app.post("/execute")
async def execute_tool(request: ExecuteRequest):
    tool = get_tool(request.tool)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")
    if not tool.enabled or not tool.implemented:
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{request.tool}' is not available in Phase {tool.phase}. Risk: {tool.risk_level}.",
        )

    if request.tool == "list_available_tools":
        return {
            "status": "success",
            "tool": request.tool,
            "data": {"formatted": format_tool_list()},
            "summary": "Tool list generated.",
        }

    return await _dispatch(request.tool, request.arguments or {})


async def _dispatch(tool_name: str, args: dict) -> dict:
    tool = get_tool(tool_name)

    import httpx

    FASTAPI_INTERNAL = os.getenv(
        "FASTAPI_INTERNAL_URL",
        "http://fastapi.agentic-app.svc.cluster.local:8000",
    )

    endpoint_map: dict[str, str] = {
        "list_vms": "/api/v1/inventory/vms",
        "get_vm_details": "/api/v1/context/vm-details",
        "get_vm_stats": "/api/v1/context/vm-details",
        "list_hosts": "/api/v1/inventory/hosts",
        "get_host_details": "/api/v1/context/host-details",
        "get_vcenter_info": "/api/v1/inventory/overview",
        "list_datastores": "/api/v1/inventory/datastores",
        "list_networks": "/api/v1/inventory/networks",
        "list_clusters": "/api/v1/inventory/clusters",
        "list_snapshots": "/api/v1/context/vm-details",
        "get_active_alarms": "/api/v1/context/active-alarms",
        "get_recent_events": "/api/v1/context/recent-events",
        "get_environment_overview": "/api/v1/context/environment",
        "get_powered_off_vms": "/api/v1/context/powered-off-vms",
        "get_datastore_health": "/api/v1/context/datastore-health",
        "get_rke2_vms": "/api/v1/context/rke2-vms",
        "search_inventory_object": "/api/v1/context/search",
        "connect_vcenter": "/api/v1/connections/vcenter/reconnect",
        "list_available_tools": "/tools",
    }

    if tool.name == "list_available_tools":
        return {
            "status": "success",
            "tool": tool.name,
            "data": {"formatted": format_tool_list()},
            "summary": "Tool list generated.",
        }

    if not tool:
        return {"status": "error", "tool": tool_name, "summary": "Tool not found in registry."}

    endpoint = endpoint_map.get(tool.name)
    if not endpoint:
        return {"status": "error", "tool": tool.name, "summary": "No execution endpoint mapped."}

    method_map: dict[str, str] = {
        "connect_vcenter": "POST",
    }

    try:
        url = f"{FASTAPI_INTERNAL}{endpoint}"
        params = {}
        if tool.name == "get_vm_details" and args.get("name"):
            params["name"] = args["name"]
        elif tool.name == "get_host_details" and args.get("host_name"):
            params["name"] = args["host_name"]
        elif tool.name == "get_host_details" and args.get("name"):
            params["name"] = args["name"]
        elif tool.name == "search_inventory_object" and args.get("q"):
            params["q"] = args["q"]
        elif tool.name == "search_inventory_object" and args.get("name"):
            params["q"] = args["name"]

        http_method = method_map.get(tool.name, "GET")
        async with httpx.AsyncClient(timeout=30.0) as client:
            if http_method == "POST":
                resp = await client.post(url, json=args)
            else:
                resp = await client.get(url, params=params)

            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("summary", "")

                if data.get("ok") is False:
                    error_code = data.get("error_code", "UNKNOWN_ERROR")
                    suggested = data.get("suggested_tool")
                    msg = data.get("message", "Tool returned an error.")
                    return {
                        "status": "error",
                        "tool": tool.name,
                        "summary": msg,
                        "error_code": error_code,
                        "suggested_tool": suggested,
                    }

                return {
                    "status": "success",
                    "tool": tool.name,
                    "data": data,
                    "summary": summary or f"Returned data for {tool.name}.",
                }

            if resp.status_code == 404:
                body = resp.json()
                return {
                    "status": "error",
                    "tool": tool.name,
                    "summary": body.get("message", "Not found"),
                    "error_code": body.get("error_code", "NOT_FOUND"),
                    "suggested_tool": body.get("suggested_tool"),
                }

            return {"status": "error", "tool": tool.name, "summary": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "tool": tool.name, "summary": str(exc)[:100]}
