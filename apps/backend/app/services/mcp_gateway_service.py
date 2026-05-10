from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.core.errors import ErrorCode
from app.schemas.mcp import MCPDiscovery, MCPServer, MCPServerStatus
from app.schemas.tools import RiskLevel, ToolSpec
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.mcp_server_registry_service import MCPServerRegistryService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService


HttpGet = Callable[[str], Awaitable[dict[str, Any]]]
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
)


class MCPGatewayService:
    def __init__(
        self,
        *,
        registry: MCPServerRegistryService | None = None,
        cache: CacheService | None = None,
        audit: AuditService | None = None,
        http_get: HttpGet | None = None,
        allowlist: set[str] | None = None,
    ) -> None:
        self.registry = registry or MCPServerRegistryService()
        self.cache = cache or CacheService()
        self.audit = audit or AuditService()
        self.http_get = http_get or self._http_get
        self.allowlist = allowlist or set()

    async def status(self, server_id: str, *, refresh: bool = False) -> MCPServerStatus:
        discovery = await self.discover(server_id, refresh=refresh)
        return discovery.status

    async def discover(self, server_id: str = "default", *, refresh: bool = False) -> MCPDiscovery:
        server = self.registry.get_server(server_id)
        if not server.enabled or not server.base_url:
            return self._discovery(
                server,
                status="not_configured",
                detail="MCP_SERVER_URL is not configured",
            )

        cache_key = f"mcp:discovery:{server.id}"
        cached = await self.cache.get(cache_key, refresh=refresh)
        if isinstance(cached, dict):
            return MCPDiscovery.model_validate({**cached, "cached": True})

        try:
            health_payload = await self._get(server, "/health")
            tools_payload = await self._get(server, "/tools")
            resources_payload = await self._get(server, "/resources")
            prompts_payload = await self._get(server, "/prompts")
        except Exception:
            status = MCPServerStatus(
                server_id=server.id,
                status="degraded",
                detail=str(ErrorCode.MCP_SERVER_UNAVAILABLE),
            )
            await self.audit.record_mcp_discovery(
                server_id=server.id,
                status="failed",
                error_code=str(ErrorCode.MCP_SERVER_UNAVAILABLE),
            )
            return MCPDiscovery(server=server, status=status)

        raw_tools = self._extract_items(tools_payload, "tools")
        resources = self._extract_items(resources_payload, "resources")
        prompts = self._extract_items(prompts_payload, "prompts")
        tools = [self.normalize_tool(server, tool) for tool in raw_tools]
        status_value = "empty" if not tools and not resources and not prompts else "healthy"
        status = MCPServerStatus(
            server_id=server.id,
            status=status_value,
            detail=str(health_payload.get("mode") or health_payload.get("status") or "MCP server reachable"),
            tool_count=len(tools),
            resource_count=len(resources),
            prompt_count=len(prompts),
        )
        discovery = MCPDiscovery(
            server=server,
            status=status,
            tools=tools,
            resources=resources,
            prompts=prompts,
        )
        await self.cache.set(cache_key, discovery.model_dump(mode="json"), ttl_seconds=30)
        await self.audit.record_mcp_discovery(
            server_id=server.id,
            status="success",
            tool_count=len(tools),
            resource_count=len(resources),
            prompt_count=len(prompts),
        )
        return discovery

    def normalize_tool(self, server: MCPServer, raw_tool: dict[str, Any]) -> ToolSpec:
        raw_name = str(raw_tool.get("name") or "unnamed").strip()
        safe_name = raw_name.replace(" ", "_").replace("/", "_")
        full_name = f"mcp.{server.id}.{safe_name}"
        risk_level = self._risk_level(raw_tool)
        allowlisted = full_name in self.allowlist
        unsafe = self._is_unsafe_name(raw_name)
        implemented = bool(allowlisted and server.trusted and risk_level == RiskLevel.READ_ONLY and not unsafe)
        enabled = implemented
        return ToolSpec(
            name=full_name,
            display_name=str(raw_tool.get("display_name") or raw_tool.get("title") or raw_name),
            description=str(raw_tool.get("description") or "Discovered MCP tool."),
            domain="mcp",
            category=str(raw_tool.get("category") or "MCP"),
            agent=str(raw_tool.get("agent") or "mcp_gateway_agent"),
            backend="mcp",
            risk_level=risk_level,
            enabled=enabled,
            implemented=implemented,
            requires_approval=risk_level != RiskLevel.READ_ONLY,
            input_schema=self._schema(raw_tool, "input_schema"),
            output_schema=self._schema(raw_tool, "output_schema"),
            mcp_server=server.id,
        )

    async def call_tool_internal(
        self,
        *,
        tool_name: str,
        tool_registry: ToolRegistryService,
        policy: PolicyService,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            tool = tool_registry.get_tool(tool_name)
        except KeyError:
            await self.audit.record_mcp_tool_attempt(
                tool_name=tool_name,
                status="blocked",
                error_code=str(ErrorCode.MCP_TOOL_NOT_FOUND),
                metadata={"reason": "tool_not_found"},
            )
            return {"ok": False, "error_code": str(ErrorCode.MCP_TOOL_NOT_FOUND), "message": "MCP tool not found."}

        decision = policy.evaluate(tool)
        if not decision.allowed:
            await self.audit.record_mcp_tool_attempt(
                tool_name=tool.name,
                status="blocked",
                risk_level=str(tool.risk_level),
                error_code=str(decision.error_code),
                metadata={"reason": decision.message},
            )
            return {"ok": False, "error_code": str(decision.error_code), "message": decision.message}

        await self.audit.record_mcp_tool_attempt(
            tool_name=tool.name,
            status="blocked",
            risk_level=str(tool.risk_level),
            error_code=str(ErrorCode.MCP_TOOL_BLOCKED),
            metadata={"reason": "public_execution_not_available", "input_keys": sorted((payload or {}).keys())},
        )
        return {
            "ok": False,
            "error_code": str(ErrorCode.MCP_TOOL_BLOCKED),
            "message": "MCP tool execution is not enabled in this phase.",
        }

    async def _get(self, server: MCPServer, path: str) -> dict[str, Any]:
        return await self.http_get(f"{server.base_url}{path}")

    async def _http_get(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("MCP server returned non-object JSON")
        return payload

    def _risk_level(self, raw_tool: dict[str, Any]) -> RiskLevel:
        risk = str(raw_tool.get("risk_level") or raw_tool.get("risk") or "").lower()
        if risk in {level.value for level in RiskLevel}:
            return RiskLevel(risk)
        return RiskLevel.APPROVAL_REQUIRED

    def _is_unsafe_name(self, name: str) -> bool:
        lower = name.lower()
        return any(marker in lower for marker in UNSAFE_NAME_MARKERS)

    def _schema(self, raw_tool: dict[str, Any], key: str) -> dict[str, Any]:
        value = raw_tool.get(key) or raw_tool.get(key.replace("_", "Schema"))
        return value if isinstance(value, dict) else {}

    def _extract_items(self, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        items = payload.get(key, [])
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def _discovery(self, server: MCPServer, *, status: str, detail: str) -> MCPDiscovery:
        return MCPDiscovery(
            server=server,
            status=MCPServerStatus(server_id=server.id, status=status, detail=detail),
        )
