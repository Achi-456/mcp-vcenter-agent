from __future__ import annotations

import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from app.core.errors import ErrorCode
from app.services.secret_store import SecretStore
from app.services.vcenter_session import VCenterCredentials, VCenterError, _truthy
from app.core.config import get_settings


Runner = Callable[..., subprocess.CompletedProcess[str]]
ALLOWED_COMMANDS = {"about", "vm.info", "host.info", "datastore.info", "events", "volume.ls", "find"}
BLOCKED_COMMANDS = {
    "vm.power",
    "vm.destroy",
    "snapshot.create",
    "snapshot.remove",
    "snapshot.revert",
    "vm.migrate",
    "host.maintenance.enter",
    "host.maintenance.exit",
    "datastore.rm",
    "datastore.cp",
    "datastore.mv",
    "object.destroy",
    "import.ova",
    "volume.rm",
}


class GovcService:
    def __init__(self, *, secret_store: SecretStore | None = None, runner: Runner | None = None) -> None:
        self.secret_store = secret_store or SecretStore()
        self.runner = runner or subprocess.run

    async def about(self) -> dict[str, Any]:
        return await self._run_json("about", ["about", "-json"])

    async def vm_info(self, name: str) -> dict[str, Any]:
        return await self._run_json("vm.info", ["vm.info", "-json", name])

    async def host_info(self, name: str) -> dict[str, Any]:
        return await self._run_json("host.info", ["host.info", "-json", name])

    async def datastore_info(self) -> dict[str, Any]:
        return await self._run_json("datastore.info", ["datastore.info", "-json"])

    async def events(self) -> dict[str, Any]:
        return await self._run_json("events", ["events", "-json"])

    async def volume_ls(self) -> dict[str, Any]:
        return await self._run_json("volume.ls", ["volume.ls", "-json"])

    async def _run_json(self, command: str, args: list[str], *, timeout_seconds: int = 30) -> dict[str, Any]:
        self._validate_command(command)
        credentials = await self._load_credentials()
        env = {
            **os.environ,
            "GOVC_URL": f"https://{credentials.host}:{credentials.port}",
            "GOVC_USERNAME": credentials.username,
            "GOVC_PASSWORD": credentials.password,
            "GOVC_INSECURE": "false" if credentials.verify_ssl else "true",
        }

        def run_sync() -> subprocess.CompletedProcess[str]:
            return self.runner(
                ["govc", *args],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )

        try:
            result = await asyncio.to_thread(run_sync)
        except subprocess.TimeoutExpired as exc:
            raise VCenterError(ErrorCode.TOOL_TIMEOUT, f"govc command '{command}' timed out.") from exc
        except OSError as exc:
            raise VCenterError(ErrorCode.VCENTER_UNREACHABLE, "govc binary or vCenter endpoint is unreachable.") from exc

        if result.returncode != 0:
            raise self._map_error(command, result.stderr or result.stdout)

        return {
            "command": command,
            "args": self._safe_args(args),
            "data": self._parse_output(result.stdout),
        }

    def _validate_command(self, command: str) -> None:
        if command in BLOCKED_COMMANDS or command not in ALLOWED_COMMANDS:
            raise VCenterError(ErrorCode.TOOL_POLICY_BLOCKED, f"govc command '{command}' is not allowed.")

    def _map_error(self, command: str, output: str) -> VCenterError:
        lower = output.lower()
        if "login" in lower or "auth" in lower or "permission" in lower:
            return VCenterError(ErrorCode.VCENTER_AUTH_FAILED, f"govc command '{command}' authentication failed.")
        if "not found" in lower:
            return VCenterError(ErrorCode.VCENTER_INVENTORY_ERROR, f"govc command '{command}' target was not found.")
        return VCenterError(
            ErrorCode.VCENTER_INVENTORY_ERROR,
            f"govc command '{command}' failed.",
            {"stderr_summary": output[:500]},
        )

    def _parse_output(self, output: str) -> Any:
        try:
            return json.loads(output) if output.strip() else {}
        except json.JSONDecodeError:
            return {"text": output.strip()}

    def _safe_args(self, args: list[str]) -> list[str]:
        return [arg for arg in args if "password" not in arg.lower()]

    async def _load_credentials(self) -> VCenterCredentials:
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
        return VCenterCredentials(
            host=parsed.hostname or url_or_host,
            username=username,
            password=password,
            verify_ssl=_truthy(data.get("VCENTER_VERIFY_SSL"), default=True),
            port=parsed.port or int(data.get("VCENTER_PORT", "443")),
        )
