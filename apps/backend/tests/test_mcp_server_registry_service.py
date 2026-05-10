from app.core.config import get_settings
from app.services.mcp_server_registry_service import MCPServerRegistryService


def test_registry_returns_default_server_from_settings(monkeypatch) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://mcp-server.test:8001")
    get_settings.cache_clear()

    server = MCPServerRegistryService().get_server("default")

    assert server.id == "default"
    assert server.base_url == "http://mcp-server.test:8001"
    assert server.enabled is True
    assert server.trusted is True
    assert server.transport == "http"

    get_settings.cache_clear()
