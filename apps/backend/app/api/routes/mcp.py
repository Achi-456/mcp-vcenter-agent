from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import mcp_gateway_dep, mcp_server_registry_dep
from app.core.errors import ErrorCode
from app.core.responses import error_response, success_response
from app.services.mcp_gateway_service import MCPGatewayService
from app.services.mcp_server_registry_service import MCPServerRegistryService

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


@router.get("/servers")
async def servers(registry: MCPServerRegistryService = Depends(mcp_server_registry_dep)) -> dict[str, Any]:
    return success_response(
        [server.model_dump(mode="json") for server in registry.list_servers()],
        source="mcp_gateway",
    )


@router.get("/servers/{server_id}/status")
async def server_status(
    server_id: str,
    refresh: bool = Query(default=False),
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
):
    try:
        status = await gateway.status(server_id, refresh=refresh)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=error_response(ErrorCode.MCP_SERVER_NOT_FOUND, f"MCP server '{server_id}' was not found."),
        )
    return success_response(status.model_dump(mode="json"), source="mcp_gateway")


@router.post("/servers/{server_id}/refresh-tools")
async def refresh_tools(
    server_id: str,
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
):
    try:
        discovery = await gateway.discover(server_id, refresh=True)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=error_response(ErrorCode.MCP_SERVER_NOT_FOUND, f"MCP server '{server_id}' was not found."),
        )
    return success_response(
        {
            "server": discovery.server.model_dump(mode="json"),
            "status": discovery.status.model_dump(mode="json"),
            "tools": [tool.model_dump(mode="json") for tool in discovery.tools],
        },
        source="mcp_gateway",
    )


@router.get("/tools")
async def tools(
    refresh: bool = Query(default=False),
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
) -> dict[str, Any]:
    discovery = await gateway.discover("default", refresh=refresh)
    return success_response(
        [tool.model_dump(mode="json") for tool in discovery.tools],
        source="mcp_gateway",
        cached=discovery.cached,
    )


@router.get("/resources")
async def resources(
    refresh: bool = Query(default=False),
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
) -> dict[str, Any]:
    discovery = await gateway.discover("default", refresh=refresh)
    return success_response(discovery.resources, source="mcp_gateway", cached=discovery.cached)


@router.get("/prompts")
async def prompts(
    refresh: bool = Query(default=False),
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
) -> dict[str, Any]:
    discovery = await gateway.discover("default", refresh=refresh)
    return success_response(discovery.prompts, source="mcp_gateway", cached=discovery.cached)
