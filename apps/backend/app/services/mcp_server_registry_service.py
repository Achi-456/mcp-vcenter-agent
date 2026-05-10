from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.schemas.mcp import MCPServer


class MCPServerRegistryService:
    def __init__(self, servers: dict[str, MCPServer] | None = None) -> None:
        self._servers = servers

    def list_servers(self) -> list[MCPServer]:
        if self._servers is not None:
            return sorted(self._servers.values(), key=lambda server: server.id)
        settings = get_settings()
        base_url = settings.mcp_server_url.strip()
        return [
            MCPServer(
                id="default",
                name="default",
                transport="http",
                base_url=base_url.rstrip("/"),
                enabled=bool(base_url),
                trusted=True,
            )
        ]

    def get_server(self, server_id: str) -> MCPServer:
        for server in self.list_servers():
            if server.id == server_id:
                return server
        raise KeyError(ErrorCode.MCP_SERVER_NOT_FOUND)
