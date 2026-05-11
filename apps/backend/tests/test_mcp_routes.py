from fastapi.testclient import TestClient

from app.api.deps import mcp_gateway_dep, mcp_server_registry_dep
from app.api.main import app
from app.schemas.mcp import MCPDiscovery, MCPServer, MCPServerStatus
from app.schemas.tools import RiskLevel, ToolSpec


class FakeRegistry:
    def __init__(self) -> None:
        self.server = MCPServer(
            id="default",
            name="default",
            base_url="http://mcp.local",
            enabled=True,
            trusted=True,
        )

    def list_servers(self):
        return [self.server]

    def get_server(self, server_id: str):
        if server_id != "default":
            raise KeyError(server_id)
        return self.server


class FakeGateway:
    def __init__(self) -> None:
        self.server = FakeRegistry().server

    async def status(self, server_id: str, *, refresh: bool = False):
        return MCPServerStatus(server_id=server_id, status="empty", detail="MCP server reachable")

    async def discover(self, server_id: str = "default", *, refresh: bool = False):
        return MCPDiscovery(
            server=self.server,
            status=MCPServerStatus(server_id=server_id, status="empty", detail="MCP server reachable"),
            tools=[
                ToolSpec(
                    name="mcp.default.server_info",
                    display_name="MCP Server Info",
                    description="Safe MCP server metadata.",
                    domain="mcp",
                    category="Diagnostics",
                    agent="mcp_diagnostic_agent",
                    backend="mcp",
                    risk_level=RiskLevel.READ_ONLY,
                    enabled=True,
                    implemented=True,
                    requires_approval=False,
                    mcp_server="default",
                )
            ],
            resources=[],
            prompts=[],
            cached=not refresh,
        )


def client() -> TestClient:
    app.dependency_overrides[mcp_server_registry_dep] = lambda: FakeRegistry()
    app.dependency_overrides[mcp_gateway_dep] = lambda: FakeGateway()
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_get_mcp_servers() -> None:
    response = client().get("/api/v1/mcp/servers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"][0]["id"] == "default"


def test_get_mcp_server_status() -> None:
    response = client().get("/api/v1/mcp/servers/default/status")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "empty"


def test_refresh_mcp_tools() -> None:
    response = client().post("/api/v1/mcp/servers/default/refresh-tools")

    assert response.status_code == 200
    assert response.json()["data"]["tools"][0]["name"] == "mcp.default.server_info"


def test_get_mcp_tools_resources_prompts() -> None:
    test_client = client()

    assert test_client.get("/api/v1/mcp/tools").json()["data"][0]["name"] == "mcp.default.server_info"
    assert test_client.get("/api/v1/mcp/resources").json()["data"] == []
    assert test_client.get("/api/v1/mcp/prompts").json()["data"] == []


def test_tools_registry_still_returns_phase2_tools() -> None:
    response = client().get("/api/v1/tools")

    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["data"]}
    assert "list_vms" in names
    assert "get_host_details" in names
    assert "mcp.default.server_info" in names


def test_get_dynamic_mcp_tool_metadata() -> None:
    response = client().get("/api/v1/tools/mcp.default.server_info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["backend"] == "mcp"
    assert payload["data"]["enabled"] is True


def test_public_mcp_execution_routes_do_not_exist() -> None:
    test_client = client()

    assert test_client.post("/api/v1/mcp/tools/mcp.default.server_info/execute").status_code == 404
    assert test_client.post("/api/v1/mcp/tools/mcp.default.server_info/call").status_code == 404
