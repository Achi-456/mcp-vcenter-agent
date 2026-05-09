from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import tool_registry_dep
from app.core.errors import ErrorCode
from app.core.responses import error_response, success_response
from app.services.tool_registry_service import ToolRegistryService

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("")
async def list_tools(registry: ToolRegistryService = Depends(tool_registry_dep)) -> dict[str, Any]:
    return success_response(
        [tool.model_dump(mode="json") for tool in registry.list_tools()],
        source="tool_registry",
    )


@router.get("/categories")
async def categories(registry: ToolRegistryService = Depends(tool_registry_dep)) -> dict[str, Any]:
    return success_response(registry.categories(), source="tool_registry")


@router.get("/agents")
async def agents(registry: ToolRegistryService = Depends(tool_registry_dep)) -> dict[str, Any]:
    return success_response(registry.agents(), source="tool_registry")


@router.get("/{tool_name}")
async def get_tool(
    tool_name: str,
    registry: ToolRegistryService = Depends(tool_registry_dep),
):
    try:
        tool = registry.get_tool(tool_name)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=error_response(
                ErrorCode.TOOL_NOT_FOUND,
                f"Tool '{tool_name}' was not found.",
            ),
        )
    return success_response(tool.model_dump(mode="json"), source="tool_registry")
