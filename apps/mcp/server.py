import os
import httpx
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, Resource

# Initialize MCP Server
mcp = Server("vCenter MCP Server")

FASTAPI_INTERNAL = os.getenv(
    "FASTAPI_INTERNAL_URL",
    "http://fastapi.agentic-app.svc.cluster.local:8000",
)

async def _proxy_call(endpoint: str, params: dict = None, data: dict = None) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{FASTAPI_INTERNAL}{endpoint}"
            if data:
                resp = await client.post(url, json=data)
            else:
                resp = await client.get(url, params=params or {})
                
            if resp.status_code == 200:
                return json.dumps(resp.json())
            return json.dumps({"error": f"HTTP {resp.status_code}", "body": resp.text})
    except Exception as exc:
        return json.dumps({"error": str(exc)})

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="list_vms", description="List all virtual machines with detailed state.", inputSchema={"type": "object", "properties": {"refresh": {"type": "boolean"}}}),
        Tool(name="get_vm_details", description="Get detailed information for a specific VM.", inputSchema={"type": "object", "properties": {"vm_name": {"type": "string"}, "refresh": {"type": "boolean"}}, "required": ["vm_name"]}),
        Tool(name="list_hosts", description="List all ESXi hosts and their status.", inputSchema={"type": "object", "properties": {"refresh": {"type": "boolean"}}}),
        Tool(name="list_datastores", description="List all datastores with capacity and usage.", inputSchema={"type": "object", "properties": {"refresh": {"type": "boolean"}}}),
        Tool(name="list_networks", description="List all networks and port groups.", inputSchema={"type": "object", "properties": {"refresh": {"type": "boolean"}}}),
        Tool(name="list_clusters", description="List all vSphere clusters.", inputSchema={"type": "object", "properties": {"refresh": {"type": "boolean"}}}),
        Tool(name="get_environment_overview", description="Get a complete vCenter environment overview: total VMs, hosts, datastores, networks, alarms.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_active_alarms", description="Get all triggered/active vCenter alarms.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_recent_events", description="Fetch recent vCenter events.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="search_inventory_object", description="Search VMs, hosts, datastores, networks by name.", inputSchema={"type": "object", "properties": {"q": {"type": "string"}, "refresh": {"type": "boolean"}}, "required": ["q"]})
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    refresh = arguments.get("refresh", False)
    
    if name == "list_vms":
        result = await _proxy_call("/api/v1/inventory/vms", {"refresh": "true" if refresh else "false"})
    elif name == "get_vm_details":
        result = await _proxy_call("/api/v1/context/vm-details", {"name": arguments.get("vm_name"), "refresh": "true" if refresh else "false"})
    elif name == "list_hosts":
        result = await _proxy_call("/api/v1/inventory/hosts", {"refresh": "true" if refresh else "false"})
    elif name == "list_datastores":
        result = await _proxy_call("/api/v1/inventory/datastores", {"refresh": "true" if refresh else "false"})
    elif name == "list_networks":
        result = await _proxy_call("/api/v1/inventory/networks", {"refresh": "true" if refresh else "false"})
    elif name == "list_clusters":
        result = await _proxy_call("/api/v1/inventory/clusters", {"refresh": "true" if refresh else "false"})
    elif name == "get_environment_overview":
        result = await _proxy_call("/api/v1/context/environment")
    elif name == "get_active_alarms":
        result = await _proxy_call("/api/v1/context/active-alarms")
    elif name == "get_recent_events":
        result = await _proxy_call("/api/v1/context/recent-events")
    elif name == "search_inventory_object":
        result = await _proxy_call("/api/v1/context/search", {"q": arguments.get("q"), "refresh": "true" if refresh else "false"})
    else:
        raise ValueError(f"Unknown tool: {name}")
        
    return [TextContent(type="text", text=result)]

@mcp.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(uri="vcenter://inventory/overview", name="vCenter Inventory Overview", description="A high-level overview of the vCenter inventory.", mimeType="application/json")
    ]

@mcp.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "vcenter://inventory/overview":
        return await _proxy_call("/api/v1/inventory/overview")
    raise ValueError(f"Unknown resource: {uri}")


sse = SseServerTransport("/messages")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the MCP server using the SSE transport
    from starlette.background import BackgroundTask
    import asyncio
    
    task = asyncio.create_task(mcp.run(sse.read_stream, sse.write_stream, mcp.create_initialization_options()))
    yield
    task.cancel()

app = FastAPI(title="vCenter MCP Server ASGI", lifespan=lifespan)

@app.get("/sse")
async def handle_sse():
    # SSE route handler
    from starlette.requests import Request
    from starlette.responses import Response
    
    async def sse_app(scope, receive, send):
        await sse.handle_sse(scope, receive, send)
    
    return sse_app

@app.post("/messages")
async def handle_messages(request: FastAPI.requests.Request):
    # Message route handler
    await sse.handle_post_message(request.scope, request.receive, request._send)
