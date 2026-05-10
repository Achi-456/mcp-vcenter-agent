import base64
from typing import Any

import structlog

from app.core.config import get_settings

log = structlog.get_logger()


class SecretStore:
    def __init__(self) -> None:
        self._client: Any | None = None

    def _load_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        try:
            from kubernetes import client, config

            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
            self._client = client.CoreV1Api()
            return self._client
        except Exception as exc:
            log.warning("kubernetes_secret_client_unavailable", error=str(exc))
            return None

    async def exists(self, secret_name: str, *, namespace: str | None = None) -> bool:
        api = self._load_client()
        if api is None:
            return False
        ns = namespace or get_settings().k8s_namespace
        try:
            api.read_namespaced_secret(secret_name, ns)
            return True
        except Exception:
            return False

    async def read_keys(self, secret_name: str, *, namespace: str | None = None) -> list[str]:
        api = self._load_client()
        if api is None:
            return []
        ns = namespace or get_settings().k8s_namespace
        try:
            secret = api.read_namespaced_secret(secret_name, ns)
            return sorted((secret.data or {}).keys())
        except Exception:
            return []

    async def read_values(
        self,
        secret_name: str,
        *,
        namespace: str | None = None,
        allowed_keys: set[str] | None = None,
    ) -> dict[str, str]:
        api = self._load_client()
        if api is None:
            return {}
        ns = namespace or get_settings().k8s_namespace
        try:
            secret = api.read_namespaced_secret(secret_name, ns)
        except Exception:
            return {}

        values: dict[str, str] = {}
        for key, encoded in (secret.data or {}).items():
            if allowed_keys is not None and key not in allowed_keys:
                continue
            values[key] = base64.b64decode(encoded).decode()
        return values

    async def write(
        self,
        secret_name: str,
        values: dict[str, str],
        *,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        api = self._load_client()
        if api is None:
            return {"secret_name": secret_name, "written": False, "reason": "kubernetes unavailable"}

        from kubernetes import client

        ns = namespace or get_settings().k8s_namespace
        data = {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}
        body = client.V1Secret(metadata=client.V1ObjectMeta(name=secret_name), data=data)
        try:
            api.patch_namespaced_secret(secret_name, ns, body)
        except Exception:
            api.create_namespaced_secret(ns, body)
        return {"secret_name": secret_name, "written": True, "keys": sorted(values.keys())}
