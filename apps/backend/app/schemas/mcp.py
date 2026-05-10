from typing import Any

from pydantic import BaseModel, Field

from app.schemas.tools import ToolSpec


class MCPServer(BaseModel):
    id: str
    name: str
    transport: str = "http"
    base_url: str
    enabled: bool
    trusted: bool


class MCPServerStatus(BaseModel):
    server_id: str
    status: str
    detail: str
    tool_count: int = 0
    resource_count: int = 0
    prompt_count: int = 0


class MCPDiscovery(BaseModel):
    server: MCPServer
    status: MCPServerStatus
    tools: list[ToolSpec] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    cached: bool = False
