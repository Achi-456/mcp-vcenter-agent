import pytest

from app.core.errors import ErrorCode
from app.schemas.mcp import MCPServer
from app.schemas.tools import RiskLevel, ToolSpec
from app.services.mcp_gateway_service import MCPGatewayService
from app.services.mcp_server_registry_service import MCPServerRegistryService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService


class FakeCache:
    def __init__(self) -> None:
        self.store = {}
        self.get_calls = []
        self.set_calls = []

    async def get(self, key: str, *, refresh: bool = False):
        self.get_calls.append((key, refresh))
        if refresh:
            return None
        return self.store.get(key)

    async def set(self, key: str, value, *, ttl_seconds: int) -> bool:
        self.set_calls.append((key, ttl_seconds))
        self.store[key] = value
        return True


class FakeAudit:
    def __init__(self) -> None:
        self.discovery_events = []
        self.tool_events = []

    async def record_mcp_discovery(self, **kwargs):
        self.discovery_events.append(kwargs)

    async def record_mcp_tool_attempt(self, **kwargs):
        self.tool_events.append(kwargs)


def registry() -> MCPServerRegistryService:
    return MCPServerRegistryService(
        {
            "default": MCPServer(
                id="default",
                name="default",
                base_url="http://mcp.local",
                enabled=True,
                trusted=True,
            )
        }
    )


@pytest.mark.asyncio
async def test_empty_mcp_discovery_returns_empty_state() -> None:
    async def http_get(url: str):
        if url.endswith("/health"):
            return {"status": "ok", "mode": "clean-rebuild-baseline"}
        if url.endswith("/tools"):
            return {"tools": []}
        if url.endswith("/resources"):
            return {"resources": []}
        return {"prompts": []}

    audit = FakeAudit()
    discovery = await MCPGatewayService(registry=registry(), cache=FakeCache(), audit=audit, http_get=http_get).discover()

    assert discovery.status.status == "empty"
    assert discovery.tools == []
    assert discovery.resources == []
    assert discovery.prompts == []
    assert audit.discovery_events[0]["status"] == "success"


@pytest.mark.asyncio
async def test_unreachable_mcp_server_returns_degraded_status() -> None:
    async def http_get(url: str):
        raise RuntimeError("connection refused")

    audit = FakeAudit()
    discovery = await MCPGatewayService(registry=registry(), cache=FakeCache(), audit=audit, http_get=http_get).discover()

    assert discovery.status.status == "degraded"
    assert discovery.status.detail == ErrorCode.MCP_SERVER_UNAVAILABLE
    assert audit.discovery_events[0]["status"] == "failed"


def test_discovered_tool_defaults_disabled_unimplemented_and_blocked() -> None:
    server = registry().get_server("default")
    tool = MCPGatewayService(registry=registry()).normalize_tool(server, {"name": "list_safe", "description": "Read"})

    assert tool.name == "mcp.default.list_safe"
    assert tool.backend == "mcp"
    assert tool.domain == "mcp"
    assert tool.enabled is False
    assert tool.implemented is False
    assert tool.risk_level == RiskLevel.APPROVAL_REQUIRED


def test_allowlisted_read_only_tool_can_be_implemented_metadata() -> None:
    server = registry().get_server("default")
    tool = MCPGatewayService(registry=registry(), allowlist={"mcp.default.list_inventory"}).normalize_tool(
        server,
        {"name": "list_inventory", "risk_level": "read_only", "input_schema": {"type": "object"}},
    )

    assert tool.enabled is True
    assert tool.implemented is True
    assert tool.requires_approval is False
    assert tool.input_schema == {"type": "object"}


def test_unsafe_tool_name_stays_disabled_even_if_allowlisted() -> None:
    server = registry().get_server("default")
    tool = MCPGatewayService(registry=registry(), allowlist={"mcp.default.shell_exec"}).normalize_tool(
        server,
        {"name": "shell_exec", "risk_level": "read_only"},
    )

    assert tool.enabled is False
    assert tool.implemented is False


@pytest.mark.asyncio
async def test_discovery_cache_and_refresh_bypass() -> None:
    calls = {"count": 0}

    async def http_get(url: str):
        calls["count"] += 1
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/tools"):
            return {"tools": []}
        if url.endswith("/resources"):
            return {"resources": []}
        return {"prompts": []}

    cache = FakeCache()
    service = MCPGatewayService(registry=registry(), cache=cache, audit=FakeAudit(), http_get=http_get)

    await service.discover()
    await service.discover()
    await service.discover(refresh=True)

    assert calls["count"] == 8
    assert cache.get_calls[0] == ("mcp:discovery:default", False)
    assert cache.get_calls[-1] == ("mcp:discovery:default", True)


@pytest.mark.asyncio
async def test_internal_call_evaluates_policy_before_blocking() -> None:
    class RecordingPolicy(PolicyService):
        def __init__(self) -> None:
            self.evaluated = False

        def evaluate(self, tool: ToolSpec):
            self.evaluated = True
            return super().evaluate(tool)

    audit = FakeAudit()
    policy = RecordingPolicy()
    service = MCPGatewayService(registry=registry(), audit=audit)
    tool_registry = ToolRegistryService(
        extra_tools=[
            ToolSpec(
                name="mcp.default.test",
                display_name="Test",
                description="Test",
                domain="mcp",
                category="MCP",
                agent="mcp_gateway_agent",
                backend="mcp",
                risk_level=RiskLevel.READ_ONLY,
                enabled=False,
                implemented=False,
                requires_approval=False,
                mcp_server="default",
            )
        ]
    )

    response = await service.call_tool_internal(tool_name="mcp.default.test", tool_registry=tool_registry, policy=policy)

    assert policy.evaluated is True
    assert response["ok"] is False
    assert audit.tool_events[0]["status"] == "blocked"
