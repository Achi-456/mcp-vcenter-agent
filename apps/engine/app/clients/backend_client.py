from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class BackendClientError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class BackendClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.backend_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.backend_timeout_seconds
        self.internal_tool_api_token = settings.internal_tool_api_token

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise BackendClientError("TOOL_TIMEOUT", f"Backend request timed out for {endpoint}.") from exc
        except httpx.HTTPError as exc:
            raise BackendClientError("AGENT_BACKEND_UNAVAILABLE", f"Backend unavailable for {endpoint}.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendClientError("INTERNAL_ERROR", f"Backend returned non-JSON response for {endpoint}.") from exc

        if not response.is_success:
            error_code = str(payload.get("error_code") or "INTERNAL_ERROR")
            message = str(payload.get("message") or f"Backend returned HTTP {response.status_code}.")
            return {"ok": False, "error_code": error_code, "message": message, "details": payload.get("details", {})}
        return payload

    async def post_internal_mcp_tool(self, tool_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.internal_tool_api_token:
            return {
                "ok": False,
                "error_code": "INTERNAL_MCP_NOT_CONFIGURED",
                "message": "Internal MCP tool access is not configured.",
                "details": {},
            }

        endpoint = f"/api/v1/internal/mcp/tools/{tool_name}/call"
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    json=payload or {},
                    headers={"X-Internal-Tool-Token": self.internal_tool_api_token},
                )
        except httpx.TimeoutException as exc:
            raise BackendClientError("TOOL_TIMEOUT", f"Backend request timed out for {endpoint}.") from exc
        except httpx.HTTPError as exc:
            raise BackendClientError("AGENT_BACKEND_UNAVAILABLE", f"Backend unavailable for {endpoint}.") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise BackendClientError("INTERNAL_ERROR", f"Backend returned non-JSON response for {endpoint}.") from exc

        if not response.is_success:
            return {
                "ok": False,
                "error_code": str(body.get("error_code") or "INTERNAL_ERROR"),
                "message": str(body.get("message") or f"Backend returned HTTP {response.status_code}."),
                "details": body.get("details", {}),
            }
        return body


async def backend_health() -> bool:
    try:
        response = await BackendClient().get("/health")
        return response.get("status") == "ok" or response.get("ok") is True
    except Exception:
        return False
