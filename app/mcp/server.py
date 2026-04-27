"""
vcenter_mcp_server.py
=====================
MCP (Model Context Protocol) server that exposes vCenter admin tools
to any MCP-compatible AI client (Claude Desktop, custom agents, etc.)

Architecture:
    MCP Client (Claude / Agent)
         │  stdio / SSE
         ▼
    vcenter_mcp_server.py   ← THIS FILE
         │  pyVmomi
         ▼
    VMware vCenter Server

Tool definitions are built dynamically from :mod:`app.tools.vcenter` via
:func:`app.tools.registry.get_dynamic_tools` — do not hand-maintain a parallel list.

Requirements:
    pip install mcp pyVmomi

Run (stdio mode for Claude Desktop):
    python vcenter_mcp_server.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "vcenter": {
          "command": "python",
          "args": ["/path/to/vcenter_mcp_server.py"],
          "env": {
            "VCENTER_HOST": "vcenter.example.com",
            "VCENTER_USER": "administrator@vsphere.local",
            "VCENTER_PASSWORD": "YourPassword"
          }
        }
      }
    }
"""

import os
import json
import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

try:
    from mcp.server import NotificationOptions
except ImportError:  # pragma: no cover
    from mcp.server.lowlevel import NotificationOptions

import app.tools.vcenter as vc
from app.tools.registry import get_dynamic_tools, invoke_tool

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MCP] %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Auto-connect from environment on startup
# ─────────────────────────────────────────────


def _auto_connect():
    host = os.environ.get("VCENTER_HOST")
    user = os.environ.get("VCENTER_USER")
    pwd = os.environ.get("VCENTER_PASSWORD")
    port = int(os.environ.get("VCENTER_PORT", 443))
    if host and user and pwd:
        result = vc.connect_vcenter(host, user, pwd, port)
        log.info(result)
    else:
        log.warning("VCENTER_HOST/USER/PASSWORD not set. Use the 'connect_vcenter' tool at runtime.")


_auto_connect()

# ─────────────────────────────────────────────
# MCP Server Setup
# ─────────────────────────────────────────────

server = Server("vcenter-admin")


def _dict_to_mcp_tool(spec: dict) -> types.Tool:
    return types.Tool(
        name=spec["name"],
        description=spec["description"],
        inputSchema=spec["input_schema"],
    )


# ─────────────────────────────────────────────
# MCP Handlers
# ─────────────────────────────────────────────


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    tool_dicts, _ = get_dynamic_tools()
    return [_dict_to_mcp_tool(t) for t in tool_dicts]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch tool calls to vcenter module functions (discovered via registry)."""
    log.info(f"Tool called: {name}({json.dumps(arguments)})")
    if arguments is None:
        arguments = {}

    try:
        _, dispatch_map = get_dynamic_tools()
        result = invoke_tool(name, arguments, dispatch_map)
        text = json.dumps(result, indent=2, default=str)
    except RuntimeError as e:
        text = json.dumps({"error": str(e)})
    except Exception as e:
        log.exception(f"Unexpected error in tool {name}")
        text = json.dumps({"error": f"Internal error: {e}"})
    else:
        if name == "connect_vcenter" and isinstance(result, str) and result.lstrip().startswith("✅"):
            await _notify_tool_list_changed()

    return [types.TextContent(type="text", text=text)]


async def _notify_tool_list_changed() -> None:
    try:
        ctx = server.request_context
    except (LookupError, AttributeError, RuntimeError):
        return
    try:
        await ctx.session.send_tool_list_changed()
    except Exception as e:
        log.debug("Tool list change notification not sent: %s", e)


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────


async def main():
    log.info("Starting vCenter MCP Server (stdio mode)...")
    notif = NotificationOptions(tools_changed=True)
    options = server.create_initialization_options(notification_options=notif)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(main())
