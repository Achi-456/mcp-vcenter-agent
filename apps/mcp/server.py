from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError


SERVER_ID = "default"
SERVER_NAME = "vCenter Agentic Ops MCP"
SERVER_VERSION = "0.2.0-safe-execution"
SAFE_TOOL_NAMES = {"server_info", "server_time", "echo_text"}
UNSAFE_NAME_MARKERS = (
    "shell",
    "exec",
    "command",
    "delete",
    "remove",
    "destroy",
    "power",
    "reboot",
    "restart",
    "migrate",
    "snapshot",
    "maintenance",
    "write",
    "patch",
    "update",
    "create",
    "upload",
    "copy",
    "move",
)


app = FastAPI(title="vCenter Agentic Ops MCP", version=SERVER_VERSION)


class EchoTextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=0, max_length=512)


TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "server_info",
        "display_name": "MCP Server Info",
        "description": "Return safe metadata about the internal MCP server.",
        "domain": "mcp",
        "category": "Diagnostics",
        "agent": "mcp_diagnostic_agent",
        "risk_level": "read_only",
        "input_schema": {"type": "object", "additionalProperties": False, "properties": {}},
        "output_schema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "server": {"type": "string"},
                "name": {"type": "string"},
                "version": {"type": "string"},
                "mode": {"type": "string"},
                "safe_execution": {"type": "boolean"},
            },
        },
    },
    {
        "name": "server_time",
        "display_name": "MCP Server Time",
        "description": "Return the current UTC timestamp from the internal MCP server.",
        "domain": "mcp",
        "category": "Diagnostics",
        "agent": "mcp_diagnostic_agent",
        "risk_level": "read_only",
        "input_schema": {"type": "object", "additionalProperties": False, "properties": {}},
        "output_schema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "utc": {"type": "string"},
            },
        },
    },
    {
        "name": "echo_text",
        "display_name": "MCP Echo Text",
        "description": "Echo a short text value for safe MCP execution validation.",
        "domain": "mcp",
        "category": "Diagnostics",
        "agent": "mcp_diagnostic_agent",
        "risk_level": "read_only",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"text": {"type": "string", "maxLength": 512}},
            "required": ["text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "text": {"type": "string"},
                "length": {"type": "integer"},
            },
        },
    },
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "tools": [tool["name"] for tool in TOOLS],
        "resources": [],
        "prompts": [],
        "mode": "safe",
        "safe_execution": True,
    }


@app.get("/tools")
async def tools() -> dict[str, list[dict[str, Any]]]:
    return {"tools": [dict(tool) for tool in TOOLS]}


@app.get("/resources")
async def resources() -> dict[str, list[Any]]:
    return {"resources": []}


@app.get("/prompts")
async def prompts() -> dict[str, list[Any]]:
    return {"prompts": []}


@app.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, payload: dict[str, Any] | None = None) -> Any:
    if _is_unsafe_name(tool_name):
        return _error("MCP_TOOL_BLOCKED", f"MCP tool '{tool_name}' is blocked.", status_code=403)
    if tool_name not in SAFE_TOOL_NAMES:
        return _error("MCP_TOOL_NOT_FOUND", f"MCP tool '{tool_name}' was not found.", status_code=404)

    payload = payload or {}
    if tool_name in {"server_info", "server_time"} and payload:
        return _error("MCP_TOOL_INVALID_INPUT", f"MCP tool '{tool_name}' does not accept input.", status_code=400)

    if tool_name == "server_info":
        return {
            "ok": True,
            "server": SERVER_ID,
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "mode": "safe",
            "safe_execution": True,
        }
    if tool_name == "server_time":
        return {
            "ok": True,
            "utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

    try:
        parsed = EchoTextInput.model_validate(payload)
    except ValidationError:
        return _error("MCP_TOOL_INVALID_INPUT", "MCP tool 'echo_text' requires text with max length 512.", status_code=400)
    return {
        "ok": True,
        "text": parsed.text,
        "length": len(parsed.text),
    }


def _is_unsafe_name(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in UNSAFE_NAME_MARKERS)


def _error(error_code: str, message: str, *, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error_code": error_code,
            "message": message,
            "details": {},
        },
    )
