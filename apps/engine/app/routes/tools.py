from fastapi import APIRouter

from app.tools.registry import list_tools, get_enabled_tools

router = APIRouter()


@router.get("/tools")
async def list_all_tools():
    all_tools = list_tools(include_disabled=True)
    enabled_tools = get_enabled_tools()
    return {
        "tools": [t.spec.model_dump() for t in all_tools],
        "enabled": [t.spec.name for t in enabled_tools],
        "categories": sorted(set(t.spec.category.value for t in all_tools)),
    }
