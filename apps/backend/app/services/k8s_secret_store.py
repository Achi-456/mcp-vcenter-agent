import base64
import os
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()

VCENTER_SECRET_NAME = "agentic-vcenter-default"
LLM_SECRET_NAME = "agentic-llm-provider-default"

_APP_NS: str | None = None


def _namespace() -> str:
    global _APP_NS
    if _APP_NS is None:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            _APP_NS = f.read().strip()
    return _APP_NS


def _kube_api():
    from kubernetes import client, config
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api()


def _b64(v: str) -> str:
    return base64.b64encode(v.encode()).decode()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_or_update_secret(name: str, data: dict[str, str], labels: dict[str, str] | None = None) -> None:
    api = _kube_api()
    ns = _namespace()
    secret_data = {k: _b64(v) for k, v in data.items()}

    try:
        existing = api.read_namespaced_secret(name, ns)
        existing.data.update(secret_data)
        api.patch_namespaced_secret(name, ns, existing)
        logger.info("k8s_secret_updated", name=name)
    except Exception:
        from kubernetes.client import V1ObjectMeta, V1Secret
        body = V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=V1ObjectMeta(name=name, labels=labels or {}),
            data=secret_data,
        )
        api.create_namespaced_secret(ns, body)
        logger.info("k8s_secret_created", name=name)


def get_secret(name: str) -> dict[str, str] | None:
    try:
        api = _kube_api()
        s = api.read_namespaced_secret(name, _namespace())
        return {k: base64.b64decode(v).decode() for k, v in s.data.items()}
    except Exception:
        return None


def delete_secret(name: str) -> bool:
    try:
        api = _kube_api()
        api.delete_namespaced_secret(name, _namespace())
        logger.info("k8s_secret_deleted", name=name)
        return True
    except Exception:
        return False


def secret_exists(name: str) -> bool:
    return get_secret(name) is not None


def mask_username(username: str) -> str:
    if not username or "@" not in username:
        return username[:3] + "***" if username else "***"
    name, domain = username.split("@", 1)
    return name[:3] + "***@" + domain
