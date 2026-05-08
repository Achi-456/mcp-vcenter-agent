from fastapi import APIRouter

from app.tools.registry import get_all_tools

router = APIRouter()


@router.get("/tools")
async def list_tools():
    tools = get_all_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "category": t.category,
                "risk": t.risk,
                "description": t.description,
                "requires_approval": t.requires_approval,
            }
            for t in tools
        ]
    }
