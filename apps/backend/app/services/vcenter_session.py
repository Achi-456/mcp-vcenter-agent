import asyncio
import ssl
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.parse import urlparse

import structlog
from pyVim import connect
from pyVmomi import vim

from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.services.secret_store import SecretStore

log = structlog.get_logger()
T = TypeVar("T")


class VCenterError(Exception):
    def __init__(self, error_code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class VCenterCredentials:
    host: str
    username: str
    password: str
    verify_ssl: bool = True
    port: int = 443

    def safe_summary(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "username_hint": self.username,
            "verify_ssl": self.verify_ssl,
            "port": self.port,
        }


def _truthy(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class VCenterSession:
    def __init__(
        self,
        *,
        secret_store: SecretStore | None = None,
        max_workers: int = 3,
    ) -> None:
        self.secret_store = secret_store or SecretStore()
        self._service_instance: Any | None = None
        self._credentials: VCenterCredentials | None = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = asyncio.Lock()

    async def load_credentials(self) -> VCenterCredentials:
        settings = get_settings()
        data = await self.secret_store.read_values(settings.vcenter_secret_name)
        if not data:
            raise VCenterError(
                ErrorCode.VCENTER_NOT_CONFIGURED,
                f"vCenter secret '{settings.vcenter_secret_name}' was not found or is unreadable.",
                {"secret_name": settings.vcenter_secret_name},
            )

        url_or_host = data.get("VCENTER_URL") or data.get("VCENTER_HOST")
        username = data.get("VCENTER_USERNAME") or data.get("VCENTER_USER")
        password = data.get("VCENTER_PASSWORD")
        if not url_or_host or not username or not password:
            raise VCenterError(
                ErrorCode.VCENTER_NOT_CONFIGURED,
                "vCenter secret is missing required host, username, or password keys.",
                {"secret_name": settings.vcenter_secret_name},
            )

        parsed = urlparse(url_or_host if "://" in url_or_host else f"https://{url_or_host}")
        host = parsed.hostname or url_or_host
        port = parsed.port or int(data.get("VCENTER_PORT", "443"))
        verify_ssl = _truthy(data.get("VCENTER_VERIFY_SSL"), default=True)
        return VCenterCredentials(host=host, username=username, password=password, verify_ssl=verify_ssl, port=port)

    async def test_connection(self) -> dict[str, Any]:
        content = await self.run(lambda _si, content: content)
        about = content.about
        return {
            "status": "connected",
            "name": about.name,
            "version": about.version,
            "build": about.build,
            "api_type": about.apiType,
        }

    async def reconnect(self) -> dict[str, Any]:
        async with self._lock:
            await self._disconnect_locked()
            self._credentials = await self.load_credentials()
            self._service_instance = await self._connect(self._credentials)
            return {"status": "reconnected", **self._credentials.safe_summary()}

    async def disconnect(self) -> None:
        async with self._lock:
            await self._disconnect_locked()

    async def run(self, func: Callable[[Any, Any], T]) -> T:
        service_instance = await self._get_or_connect()
        try:
            return await self._run_with_instance(service_instance, func)
        except vim.fault.NotAuthenticated:
            async with self._lock:
                await self._disconnect_locked()
                self._credentials = await self.load_credentials()
                self._service_instance = await self._connect(self._credentials)
                service_instance = self._service_instance
            try:
                return await self._run_with_instance(service_instance, func)
            except vim.fault.NotAuthenticated as exc:
                raise VCenterError(
                    ErrorCode.VCENTER_SESSION_EXPIRED,
                    "vCenter session expired after one reconnect attempt.",
                ) from exc
        except vim.fault.InvalidLogin as exc:
            raise VCenterError(ErrorCode.VCENTER_AUTH_FAILED, "vCenter authentication failed.") from exc
        except ssl.SSLError as exc:
            raise VCenterError(ErrorCode.VCENTER_SSL_ERROR, "vCenter SSL validation failed.") from exc
        except OSError as exc:
            raise VCenterError(ErrorCode.VCENTER_UNREACHABLE, "vCenter is unreachable.") from exc

    async def _get_or_connect(self) -> Any:
        async with self._lock:
            if self._service_instance is not None and await self._has_current_session(self._service_instance):
                return self._service_instance
            await self._disconnect_locked()
            self._credentials = await self.load_credentials()
            self._service_instance = await self._connect(self._credentials)
            return self._service_instance

    async def _connect(self, credentials: VCenterCredentials) -> Any:
        loop = asyncio.get_running_loop()
        context = None
        if not credentials.verify_ssl:
            context = ssl._create_unverified_context()

        def connect_sync() -> Any:
            return connect.SmartConnect(
                host=credentials.host,
                user=credentials.username,
                pwd=credentials.password,
                port=credentials.port,
                sslContext=context,
            )

        try:
            return await loop.run_in_executor(self._executor, connect_sync)
        except vim.fault.InvalidLogin as exc:
            raise VCenterError(ErrorCode.VCENTER_AUTH_FAILED, "vCenter authentication failed.") from exc
        except ssl.SSLError as exc:
            raise VCenterError(ErrorCode.VCENTER_SSL_ERROR, "vCenter SSL validation failed.") from exc
        except OSError as exc:
            raise VCenterError(ErrorCode.VCENTER_UNREACHABLE, "vCenter is unreachable.") from exc

    async def _run_with_instance(self, service_instance: Any, func: Callable[[Any, Any], T]) -> T:
        loop = asyncio.get_running_loop()

        def run_sync() -> T:
            content = service_instance.RetrieveContent()
            return func(service_instance, content)

        return await loop.run_in_executor(self._executor, run_sync)

    async def _has_current_session(self, service_instance: Any) -> bool:
        try:
            content = await self._run_with_instance(service_instance, lambda _si, content: content)
            return content.sessionManager.currentSession is not None
        except vim.fault.NotAuthenticated:
            return False
        except Exception:
            return False

    async def _disconnect_locked(self) -> None:
        if self._service_instance is None:
            return
        service_instance = self._service_instance
        self._service_instance = None
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, connect.Disconnect, service_instance)


_session: VCenterSession | None = None


def get_vcenter_session() -> VCenterSession:
    global _session
    if _session is None:
        _session = VCenterSession()
    return _session


def reset_vcenter_session() -> VCenterSession:
    global _session
    _session = VCenterSession()
    return _session
