from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.services.secret_store import SecretStore
from app.services.vcenter_session import VCenterCredentials, VCenterError, _truthy


class VSphereRestService:
    def __init__(
        self,
        *,
        secret_store: SecretStore | None = None,
        client_factory=httpx.AsyncClient,
        timeout_seconds: float = 20,
    ) -> None:
        self.secret_store = secret_store or SecretStore()
        self.client_factory = client_factory
        self.timeout_seconds = timeout_seconds
        self._credentials: VCenterCredentials | None = None
        self._session_id: str | None = None

    async def about(self) -> dict[str, Any]:
        return await self._get_result("/rest/appliance/system/version")

    async def appliance_health(self) -> dict[str, Any]:
        return await self._get_result("/rest/appliance/health/system")

    async def list_tag_categories(self) -> dict[str, Any]:
        return await self._get_result("/rest/com/vmware/cis/tagging/category")

    async def list_tags(self) -> dict[str, Any]:
        return await self._get_result("/rest/com/vmware/cis/tagging/tag")

    async def list_attached_tags(self, object_id: str) -> dict[str, Any]:
        return await self._post_result(
            "/rest/com/vmware/cis/tagging/tag-association?~action=list-attached-tags",
            {"object_id": {"id": object_id, "type": "VirtualMachine"}},
        )

    async def list_content_libraries(self) -> dict[str, Any]:
        return await self._get_result("/rest/com/vmware/content/library")

    async def list_library_items(self, library_id: str) -> dict[str, Any]:
        return await self._get_result(f"/rest/com/vmware/content/library/item?library_id={library_id}")

    async def list_recent_tasks(self) -> dict[str, Any]:
        data = await self._request("GET", "/rest/cis/tasks", params={"filter_spec": "{}"})
        return {"endpoint": "/rest/cis/tasks", "data": data}

    async def _get_result(self, endpoint: str) -> dict[str, Any]:
        data = await self._request("GET", endpoint)
        return {"endpoint": endpoint, "data": data}

    async def _post_result(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request("POST", endpoint, json=payload)
        return {"endpoint": endpoint, "data": data}

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        credentials = await self._get_credentials()
        session_id = await self._get_session(credentials)
        response = await self._send(credentials, method, endpoint, session_id=session_id, json=json, params=params)
        if response.status_code == 401:
            self._session_id = None
            session_id = await self._login(credentials)
            response = await self._send(credentials, method, endpoint, session_id=session_id, json=json, params=params)
        if response.status_code in {401, 403}:
            raise VCenterError(ErrorCode.VCENTER_AUTH_FAILED, "vSphere REST authentication failed.")
        if response.status_code == 404:
            raise VCenterError(
                ErrorCode.VCENTER_INVENTORY_ERROR,
                f"vSphere REST endpoint is unsupported or not found: {endpoint}",
                {"endpoint": endpoint, "status_code": response.status_code},
            )
        if response.status_code >= 400:
            raise VCenterError(
                ErrorCode.VCENTER_INVENTORY_ERROR,
                "vSphere REST request failed.",
                {"endpoint": endpoint, "status_code": response.status_code, "message": response.text[:500]},
            )
        try:
            payload = response.json()
        except ValueError:
            return {"text": response.text}
        return payload.get("value", payload) if isinstance(payload, dict) else payload

    async def _send(
        self,
        credentials: VCenterCredentials,
        method: str,
        endpoint: str,
        *,
        session_id: str,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with self.client_factory(
            base_url=f"https://{credentials.host}:{credentials.port}",
            verify=credentials.verify_ssl,
            timeout=self.timeout_seconds,
        ) as client:
            return await client.request(
                method,
                endpoint,
                headers={"vmware-api-session-id": session_id},
                json=json,
                params=params,
            )

    async def _get_session(self, credentials: VCenterCredentials) -> str:
        if self._session_id:
            return self._session_id
        return await self._login(credentials)

    async def _login(self, credentials: VCenterCredentials) -> str:
        try:
            async with self.client_factory(
                base_url=f"https://{credentials.host}:{credentials.port}",
                verify=credentials.verify_ssl,
                timeout=self.timeout_seconds,
            ) as client:
                response = await client.post(
                    "/rest/com/vmware/cis/session",
                    auth=(credentials.username, credentials.password),
                )
        except httpx.HTTPError as exc:
            raise VCenterError(ErrorCode.VCENTER_UNREACHABLE, "vSphere REST endpoint is unreachable.") from exc
        if response.status_code in {401, 403}:
            raise VCenterError(ErrorCode.VCENTER_AUTH_FAILED, "vSphere REST authentication failed.")
        if response.status_code >= 400:
            raise VCenterError(
                ErrorCode.VCENTER_INVENTORY_ERROR,
                "vSphere REST login failed.",
                {"status_code": response.status_code, "message": response.text[:500]},
            )
        value = response.json().get("value")
        if not value:
            raise VCenterError(ErrorCode.VCENTER_AUTH_FAILED, "vSphere REST did not return a session token.")
        self._session_id = str(value)
        return self._session_id

    async def _get_credentials(self) -> VCenterCredentials:
        if self._credentials is not None:
            return self._credentials
        settings = get_settings()
        data = await self.secret_store.read_values(settings.vcenter_secret_name)
        if not data:
            raise VCenterError(
                ErrorCode.VCENTER_NOT_CONFIGURED,
                f"vCenter secret '{settings.vcenter_secret_name}' was not found or is unreadable.",
            )
        url_or_host = data.get("VCENTER_URL") or data.get("VCENTER_HOST")
        username = data.get("VCENTER_USERNAME") or data.get("VCENTER_USER")
        password = data.get("VCENTER_PASSWORD")
        if not url_or_host or not username or not password:
            raise VCenterError(ErrorCode.VCENTER_NOT_CONFIGURED, "vCenter secret is missing required keys.")
        parsed = urlparse(url_or_host if "://" in url_or_host else f"https://{url_or_host}")
        self._credentials = VCenterCredentials(
            host=parsed.hostname or url_or_host,
            username=username,
            password=password,
            verify_ssl=_truthy(data.get("VCENTER_VERIFY_SSL"), default=True),
            port=parsed.port or int(data.get("VCENTER_PORT", "443")),
        )
        return self._credentials
