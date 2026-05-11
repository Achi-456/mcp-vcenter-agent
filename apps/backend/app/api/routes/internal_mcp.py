from hmac import compare_digest
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.api.deps import mcp_gateway_dep, policy_dep, settings_dep, tool_registry_dep
from app.core.config import Settings
from app.core.errors import ErrorCode
from app.core.responses import error_response
from app.services.mcp_gateway_service import DEFAULT_MCP_TOOL_ALLOWLIST, MCPGatewayService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService

router = APIRouter(prefix="/api/v1/internal/mcp", tags=["internal-mcp"])


def _reject(message: str = "Internal MCP tool endpoint is disabled or unauthorized.") -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=error_response(ErrorCode.TOOL_POLICY_BLOCKED, message),
    )


def validate_internal_tool_token(
    x_internal_tool_token: str | None = Header(default=None, alias="X-Internal-Tool-Token"),
    settings: Settings = Depends(settings_dep),
) -> None | JSONResponse:
    configured_token = settings.internal_tool_api_token
    if not configured_token or not x_internal_tool_token:
        return _reject()
    if not compare_digest(x_internal_tool_token, configured_token):
        return _reject()
    return None


@router.post("/tools/{tool_name}/call", response_model=None)
async def call_internal_mcp_tool(
    tool_name: str,
    payload: dict[str, Any] | None = None,
    token_error: None | JSONResponse = Depends(validate_internal_tool_token),
    gateway: MCPGatewayService = Depends(mcp_gateway_dep),
    tool_registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
):
    if token_error is not None:
        return token_error

    if tool_name not in DEFAULT_MCP_TOOL_ALLOWLIST:
        return JSONResponse(
            status_code=404,
            content=error_response(ErrorCode.MCP_TOOL_NOT_FOUND, "MCP tool not found."),
        )

    response = await gateway.call_tool_internal(
        tool_name=tool_name,
        tool_registry=tool_registry,
        policy=policy,
        payload=payload or {},
    )
    if response.get("ok") is True:
        response.setdefault("metadata", {})
        response["metadata"]["tool"] = tool_name
    return response
