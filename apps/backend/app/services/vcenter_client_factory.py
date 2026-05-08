"""
Persistent vCenter session singleton.

Replaces the old with_vcenter() per-request connection pattern.
One ServiceInstance is kept alive for the lifetime of the FastAPI pod.
Before every call, the session is validated. On NotAuthenticated,
the session is re-established and the call is retried exactly once.
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

import structlog
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim, vmodl

from app.core.inventory_errors import error_response
from app.services.k8s_secret_store import VCENTER_SECRET_NAME, get_secret

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=4)
T = TypeVar("T")


# ── Credential loader ─────────────────────────────────────────────────────────


def get_vcenter_credentials() -> dict | None:
    s = get_secret(VCENTER_SECRET_NAME)
    if not s:
        return None
    url  = s.get("VCENTER_URL", "")
    user = s.get("VCENTER_USERNAME", "")
    pwd  = s.get("VCENTER_PASSWORD", "")
    ssl  = s.get("VCENTER_VERIFY_SSL", "false") == "true"
    if not url or not user or not pwd:
        return None
    return {"url": url, "username": user, "password": pwd, "verify_ssl": ssl}


def _parse_host_port(url: str) -> tuple[str, int]:
    host = url.replace("https://", "").replace("http://", "").split("/")[0]
    port = 443
    if ":" in host:
        host, port_str = host.split(":", 1)
        port = int(port_str)
    return host, port


# ── Singleton session ─────────────────────────────────────────────────────────


class VCenterSession:
    """
    Thread-safe singleton holding one persistent pyVmomi ServiceInstance.

    Usage:
        result = vcenter_session.run(lambda si, content: list_vms(si, content))
        result = vcenter_session.run(list_vms)

    The session is created lazily on the first call and kept alive between
    calls. If the session expires or vCenter restarts, it is automatically
    re-established and the call is retried once.
    """

    def __init__(self) -> None:
        self._si: vim.ServiceInstance | None = None
        self._content: vim.ServiceContent | None = None
        self._creds: dict | None = None
        self._lock = threading.Lock()

    # ── Internal: connection management ──────────────────────────────────────

    def _do_connect(self, creds: dict) -> None:
        """Establish a new ServiceInstance. Caller must hold self._lock."""
        host, port = _parse_host_port(creds["url"])
        logger.info("vcenter_connecting", host=host)
        si = SmartConnect(
            host=host,
            user=creds["username"],
            pwd=creds["password"],
            port=port,
            disableSslCertValidation=not creds["verify_ssl"],
        )
        self._si = si
        self._content = si.RetrieveContent()
        self._creds = creds
        logger.info("vcenter_connected", host=host)

    def _disconnect_quiet(self) -> None:
        """Disconnect without raising. Used before reconnect."""
        try:
            if self._si is not None:
                Disconnect(self._si)
        except Exception:
            pass
        finally:
            self._si = None
            self._content = None

    def _is_alive(self) -> bool:
        """Ping the session manager. Returns False on any error."""
        try:
            session = self._si.content.sessionManager.currentSession  # type: ignore[union-attr]
            return session is not None
        except Exception:
            return False

    def _ensure_connected(self) -> dict | None:
        """
        Ensure there is a live session.
        Returns error_response dict on failure, None on success.
        Caller must hold self._lock.
        """
        creds = get_vcenter_credentials()
        if not creds:
            return error_response("VCENTER_NOT_CONFIGURED")
        if self._si is not None and self._is_alive():
            return None
        self._disconnect_quiet()
        try:
            self._do_connect(creds)
            return None
        except Exception as exc:
            msg = str(exc).lower()
            logger.warning("vcenter_connect_failed", error=str(exc)[:120])
            if "auth" in msg or "login" in msg or "password" in msg:
                return error_response("VCENTER_AUTH_FAILED")
            if "refused" in msg or "timeout" in msg or "unreachable" in msg:
                return error_response("VCENTER_UNREACHABLE")
            if "ssl" in msg or "certificate" in msg:
                return error_response("VCENTER_SSL_ERROR")
            return error_response("VCENTER_INVENTORY_ERROR")

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, fn: Callable[[vim.ServiceInstance, vim.ServiceContent], T]) -> T | dict:
        """
        Run fn(si, content) with a live session.

        On NotAuthenticated:
          1. Clear session
          2. Reconnect
          3. Retry fn once

        Returns error_response dict on unrecoverable failure.
        """
        with self._lock:
            err = self._ensure_connected()
            if err:
                return err

            try:
                return fn(self._si, self._content)  # type: ignore[arg-type]

            except (vim.fault.NotAuthenticated, vmodl.fault.SystemError) as exc:
                logger.warning("vcenter_session_expired_retrying", error=type(exc).__name__)
                self._disconnect_quiet()
                retry_err = self._ensure_connected()
                if retry_err:
                    return retry_err
                try:
                    return fn(self._si, self._content)  # type: ignore[arg-type]
                except Exception as retry_exc:
                    logger.error("vcenter_retry_failed", error=str(retry_exc)[:120])
                    return error_response("VCENTER_SESSION_EXPIRED")

            except Exception as exc:
                msg = str(exc).lower()
                logger.error("vcenter_call_failed", error=str(exc)[:120])
                if "auth" in msg or "login" in msg:
                    return error_response("VCENTER_AUTH_FAILED")
                if "refused" in msg or "timeout" in msg:
                    return error_response("VCENTER_UNREACHABLE")
                return error_response("VCENTER_INVENTORY_ERROR")

    def force_reconnect(self) -> dict | None:
        """
        Force a fresh connection regardless of current session state.
        Returns error_response on failure, None on success.
        """
        with self._lock:
            logger.info("vcenter_force_reconnect")
            self._disconnect_quiet()
            return self._ensure_connected()

    def status(self) -> dict:
        """Return connection status for /health and monitoring endpoints."""
        with self._lock:
            if self._si is None:
                return {"connected": False, "reason": "no_session"}
            alive = self._is_alive()
            return {
                "connected": alive,
                "host": self._creds["url"] if self._creds else None,
                "reason": "ok" if alive else "session_expired",
            }


# ── Module-level singleton ────────────────────────────────────────────────────

vcenter_session = VCenterSession()


# ── Backwards-compatible helpers ──────────────────────────────────────────────


def with_vcenter(fn: Callable) -> Any:
    return vcenter_session.run(fn)


async def async_with_vcenter(fn: Callable) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, vcenter_session.run, fn)


def connect_to_vcenter(creds: dict):
    """Backwards-compatible. Used by vcenter_connection_service.py test endpoint."""
    host, port = _parse_host_port(creds["url"])
    return SmartConnect(
        host=host,
        user=creds["username"],
        pwd=creds["password"],
        port=port,
        disableSslCertValidation=not creds["verify_ssl"],
    )


def disconnect_from_vcenter(si) -> None:
    try:
        Disconnect(si)
    except Exception:
        pass
