import os
import httpx

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://mcp-server.agentic-app.svc.cluster.local:8001",
)


async def get_tools_from_mcp(enabled_only: bool = True) -> list[dict]:
    """Fetch tool registry from MCP server."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{MCP_SERVER_URL}/tools",
                params={"enabled_only": str(enabled_only).lower()},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tools", [])
    except Exception:
        pass
    return []


async def execute_tool_via_mcp(tool_name: str, args: dict | None = None) -> dict:
    """Execute a tool through the MCP server."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{MCP_SERVER_URL}/execute",
                json={"tool": tool_name, "arguments": args or {}},
            )
            if resp.status_code == 200:
                result = resp.json()
                # Never treat error results as cacheable success
                return result
            return {
                "status": "error",
                "tool": tool_name,
                "summary": f"MCP HTTP {resp.status_code}",
                "cacheable": False,
            }
    except Exception as exc:
        return {
            "status": "error",
            "tool": tool_name,
            "summary": str(exc)[:100],
            "cacheable": False,
        }


async def get_formatted_tool_list() -> str:
    """Get the formatted Markdown tool list from MCP server."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{MCP_SERVER_URL}/tools")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tool_list_formatted", "")
    except Exception:
        pass
    return "Tool registry is temporarily unavailable."
