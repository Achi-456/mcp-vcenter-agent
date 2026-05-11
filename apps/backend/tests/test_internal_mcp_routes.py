from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import mcp_gateway_dep, policy_dep, settings_dep, tool_registry_dep
from app.api.main import app
from app.core.config import Settings
from app.core.errors import ErrorCode
from app.schemas.mcp import MCPDiscovery, MCPServer, MCPServerStatus
from app.schemas.tools import RiskLevel, ToolSpec
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def discover(self, server_id: str = "default", *, refresh: bool = False) -> MCPDiscovery:
        server = MCPServer(
            id=server_id,
            name=server_id,
            base_url="http://mcp.local",
            enabled=True,
            trusted=True,
        )
        return MCPDiscovery(
            server=server,
            status=MCPServerStatus(server_id=server_id, status="healthy", detail="safe"),
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

    async def call_tool_internal(
        self,
        *,
        tool_name: str,
        tool_registry: ToolRegistryService,
        policy: PolicyService,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = payload or {}
        self.calls.append({"tool_name": tool_name, "payload": payload})
        if tool_name == "mcp.default.echo_text" and len(str(payload.get("text", ""))) > 512:
            return {
                "ok": False,
                "error_code": str(ErrorCode.MCP_TOOL_INVALID_INPUT),
                "message": "echo_text input exceeds 512 characters.",
                "details": {},
            }
        data: dict[str, Any] = {"ok": True}
        if tool_name == "mcp.default.server_info":
            data.update({"server": "default", "name": "test-mcp", "mode": "safe"})
        elif tool_name == "mcp.default.server_time":
            data.update({"utc": "2026-05-11T00:00:00Z"})
        elif tool_name == "mcp.default.echo_text":
            text = str(payload.get("text", ""))
            data.update({"text": text, "length": len(text)})
        return {"ok": True, "data": data, "metadata": {"source": "mcp", "cached": False}}


def client(*, token: str | None = "test-token", gateway: FakeGateway | None = None) -> tuple[TestClient, FakeGateway]:
    fake_gateway = gateway or FakeGateway()
    app.dependency_overrides[mcp_gateway_dep] = lambda: fake_gateway
    app.dependency_overrides[tool_registry_dep] = lambda: ToolRegistryService()
    app.dependency_overrides[policy_dep] = lambda: PolicyService()
    app.dependency_overrides[settings_dep] = lambda: Settings(internal_tool_api_token=token)
    return TestClient(app), fake_gateway


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_missing_internal_token_is_rejected() -> None:
    test_client, gateway = client()

    response = test_client.post("/api/v1/internal/mcp/tools/mcp.default.server_info/call", json={})

    assert response.status_code == 403
    assert response.json()["ok"] is False
    assert gateway.calls == []


def test_wrong_internal_token_is_rejected() -> None:
    test_client, gateway = client()

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.server_info/call",
        headers={"X-Internal-Tool-Token": "wrong"},
        json={},
    )

    assert response.status_code == 403
    assert response.json()["ok"] is False
    assert gateway.calls == []


def test_unconfigured_internal_token_disables_endpoint() -> None:
    test_client, gateway = client(token=None)

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.server_info/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={},
    )

    assert response.status_code == 403
    assert response.json()["ok"] is False
    assert gateway.calls == []


def test_correct_token_allows_server_info() -> None:
    test_client, gateway = client()

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.server_info/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["server"] == "default"
    assert payload["metadata"]["source"] == "mcp"
    assert payload["metadata"]["tool"] == "mcp.default.server_info"
    assert gateway.calls[0]["tool_name"] == "mcp.default.server_info"


def test_correct_token_allows_server_time() -> None:
    test_client, gateway = client()

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.server_time/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={},
    )

    assert response.status_code == 200
    assert response.json()["data"]["utc"] == "2026-05-11T00:00:00Z"
    assert gateway.calls[0]["tool_name"] == "mcp.default.server_time"


def test_correct_token_allows_echo_text_with_safe_input() -> None:
    test_client, gateway = client()

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.echo_text/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={"text": "hello"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["length"] == 5
    assert gateway.calls[0]["payload"] == {"text": "hello"}


def test_echo_text_over_512_chars_is_rejected_cleanly() -> None:
    test_client, gateway = client()

    response = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.echo_text/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={"text": "x" * 513},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == ErrorCode.MCP_TOOL_INVALID_INPUT
    assert gateway.calls[0]["tool_name"] == "mcp.default.echo_text"


def test_unknown_and_suspicious_tools_are_not_routed() -> None:
    test_client, gateway = client()

    unknown = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.delete_file/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={},
    )
    suspicious = test_client.post(
        "/api/v1/internal/mcp/tools/mcp.default.run_shell/call",
        headers={"X-Internal-Tool-Token": "test-token"},
        json={},
    )

    assert unknown.status_code == 404
    assert suspicious.status_code == 404
    assert unknown.json()["error_code"] == ErrorCode.MCP_TOOL_NOT_FOUND
    assert suspicious.json()["error_code"] == ErrorCode.MCP_TOOL_NOT_FOUND
    assert gateway.calls == []


def test_public_mcp_execution_routes_still_do_not_exist() -> None:
    test_client, _ = client()

    assert test_client.post("/api/v1/mcp/tools/mcp.default.server_info/execute").status_code == 404
    assert test_client.post("/api/v1/mcp/tools/mcp.default.server_info/call").status_code == 404


def test_public_mcp_tools_remains_metadata_only() -> None:
    test_client, _ = client()

    assert test_client.get("/api/v1/mcp/tools").status_code == 200
    assert test_client.post("/api/v1/mcp/tools").status_code == 405
