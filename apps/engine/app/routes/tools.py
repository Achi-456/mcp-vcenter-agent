from fastapi import APIRouter

import os
import httpx

router = APIRouter()

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://mcp-server.agentic-app.svc.cluster.local:8001",
)


@router.get("/tools")
async def list_tools():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{MCP_SERVER_URL}/tools")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"tools": [], "categories": []}
