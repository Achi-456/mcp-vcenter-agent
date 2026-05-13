from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import Settings, get_settings
from app.services.secret_store import SecretStore

log = structlog.get_logger()


PROVIDER_API_KEY_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class LLMModelService:
    def __init__(self, settings: Settings | None = None, secret_store: SecretStore | None = None) -> None:
        self.settings = settings or get_settings()
        self.secret_store = secret_store or SecretStore()

    async def providers(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "configured": await self._backend_discovery_configured("gemini"),
                "models_endpoint": "/api/v1/llm/models?provider=gemini",
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "configured": await self._backend_discovery_configured("openai"),
                "models_endpoint": "/api/v1/llm/models?provider=openai",
            },
        ]

    async def status(self) -> dict[str, Any]:
        provider = self.settings.llm_provider.strip().lower()
        backend_configured = await self._backend_discovery_configured(provider)
        runtime = await self._engine_runtime_status(provider)

        missing_requirements: list[str] = []
        if not self.settings.llm_enabled:
            missing_requirements.append("LLM_ENABLED is false")
        if not self.settings.llm_model:
            missing_requirements.append("LLM_MODEL is not configured")
        key_name = PROVIDER_API_KEY_NAMES.get(provider)
        if not backend_configured and key_name:
            missing_requirements.append(f"backend discovery credential for {provider} is not configured")
        missing_requirements.extend(runtime["missing_requirements"])

        ready = self.settings.llm_enabled and backend_configured and runtime["configured"] and bool(self.settings.llm_model)
        return {
            "llm_enabled": self.settings.llm_enabled,
            "active_provider": provider,
            "active_model": self.settings.llm_model,
            "backend_discovery_configured": backend_configured,
            "engine_runtime_configured": runtime["configured"],
            "missing_requirements": missing_requirements,
            "status": "ready" if ready else "not_configured",
        }

    async def list_models(self, provider: str) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider == "gemini":
            return await self._list_gemini_models()
        if provider == "openai":
            return await self._list_openai_models()
        return {"provider": provider, "configured": False, "models": [], "error": "Unsupported provider."}

    async def configure_provider(self, provider: str, api_key: str) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider not in PROVIDER_API_KEY_NAMES:
            return {
                "provider": provider,
                "backend_discovery_configured": False,
                "engine_runtime_configured": False,
                "engine_runtime_updated": False,
                "error": f"Unsupported provider: {provider}",
            }

        key_name = PROVIDER_API_KEY_NAMES[provider]
        existing = await self.secret_store.read_values(
            self.settings.llm_secret_name,
            namespace=self.settings.k8s_namespace,
            allowed_keys=set(PROVIDER_API_KEY_NAMES.values()),
        )
        existing[key_name] = api_key
        write_result = await self.secret_store.write(
            self.settings.llm_secret_name,
            existing,
            namespace=self.settings.k8s_namespace,
        )
        if not write_result.get("written"):
            return {
                "provider": provider,
                "backend_discovery_configured": False,
                "engine_runtime_configured": False,
                "engine_runtime_updated": False,
                "error": write_result.get("reason", "Failed to write backend discovery secret."),
                "message": "Backend discovery was not configured. Agent Engine runtime was not changed.",
            }

        if provider == "gemini":
            self.settings.gemini_api_key = api_key
        elif provider == "openai":
            self.settings.openai_api_key = api_key

        runtime = await self._engine_runtime_status(provider)
        return {
            "provider": provider,
            "backend_discovery_configured": True,
            "engine_runtime_configured": runtime["configured"],
            "engine_runtime_updated": False,
            "secret_name": self.settings.llm_secret_name,
            "secret_namespace": self.settings.k8s_namespace,
            "runtime_namespace": self.settings.llm_runtime_namespace,
            "missing_requirements": runtime["missing_requirements"],
            "message": (
                "Backend discovery secret saved. Agent Engine runtime was not changed; "
                "mount the provider key and LLM env vars on the Agent Engine deployment before expecting LLM answers."
            ),
        }

    async def _list_gemini_models(self) -> dict[str, Any]:
        api_key = await self._backend_discovery_api_key("gemini")
        if not api_key:
            return {"provider": "gemini", "configured": False, "models": []}
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": api_key},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            log.warning("llm_model_discovery_failed", provider="gemini")
            return {"provider": "gemini", "configured": True, "models": [], "error": "Model discovery failed."}

        models = []
        for item in payload.get("models", []):
            methods = item.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            name = str(item.get("name", ""))
            model_id = name.removeprefix("models/")
            models.append(
                {
                    "id": model_id,
                    "name": name,
                    "display_name": item.get("displayName") or model_id,
                    "description": item.get("description") or "",
                    "input_token_limit": item.get("inputTokenLimit"),
                    "output_token_limit": item.get("outputTokenLimit"),
                    "supported_generation_methods": methods,
                }
            )
        return {"provider": "gemini", "configured": True, "models": models}

    async def _list_openai_models(self) -> dict[str, Any]:
        api_key = await self._backend_discovery_api_key("openai")
        if not api_key:
            return {"provider": "openai", "configured": False, "models": []}
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            log.warning("llm_model_discovery_failed", provider="openai")
            return {"provider": "openai", "configured": True, "models": [], "error": "Model discovery failed."}

        models = [
            {
                "id": str(item.get("id")),
                "name": str(item.get("id")),
                "display_name": str(item.get("id")),
                "created": item.get("created"),
                "owned_by": item.get("owned_by"),
            }
            for item in payload.get("data", [])
            if item.get("id")
        ]
        return {"provider": "openai", "configured": True, "models": models}

    async def _backend_discovery_configured(self, provider: str) -> bool:
        return bool(await self._backend_discovery_api_key(provider))

    async def _backend_discovery_api_key(self, provider: str) -> str | None:
        key_name = PROVIDER_API_KEY_NAMES.get(provider)
        if not key_name:
            return None
        env_value = self._env_api_key(provider)
        if env_value:
            return env_value
        values = await self.secret_store.read_values(
            self.settings.llm_secret_name,
            namespace=self.settings.k8s_namespace,
            allowed_keys={key_name},
        )
        return values.get(key_name)

    def _env_api_key(self, provider: str) -> str | None:
        if provider == "gemini":
            return self.settings.gemini_api_key
        if provider == "openai":
            return self.settings.openai_api_key
        return None

    async def _engine_runtime_status(self, provider: str) -> dict[str, Any]:
        key_name = PROVIDER_API_KEY_NAMES.get(provider)
        if not key_name:
            return {"configured": False, "missing_requirements": [f"unsupported provider {provider}"]}

        deployment = self._read_engine_deployment()
        if deployment is None:
            return {
                "configured": False,
                "missing_requirements": [f"agent-engine deployment not readable in {self.settings.llm_runtime_namespace}"],
            }

        env_map = self._deployment_env_map(deployment)
        mounted = self._env_is_mounted(env_map.get(key_name))
        if not mounted:
            return {"configured": False, "missing_requirements": [f"agent-engine provider credential for {provider} is not mounted"]}

        missing: list[str] = []
        enabled_env = env_map.get("LLM_ENABLED")
        if not enabled_env or getattr(enabled_env, "value", None) not in ("true", "True", "1"):
            missing.append("agent-engine LLM_ENABLED is not true")
        provider_env = env_map.get("LLM_PROVIDER")
        if not provider_env:
            missing.append(f"agent-engine LLM_PROVIDER not mounted as {provider}")
        elif getattr(provider_env, "value", None) and str(provider_env.value).lower() != provider:
            missing.append(f"agent-engine LLM_PROVIDER is not {provider}")
        if not self._env_is_mounted(env_map.get("LLM_MODEL")):
            missing.append("agent-engine LLM_MODEL not mounted")

        return {"configured": not missing, "missing_requirements": missing}

    def _read_engine_deployment(self) -> Any | None:
        try:
            from kubernetes import client, config

            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
            return client.AppsV1Api().read_namespaced_deployment(
                self.settings.llm_engine_deployment_name,
                self.settings.llm_runtime_namespace,
            )
        except Exception:
            log.info("llm_engine_runtime_status_unavailable")
            return None

    def _deployment_env_map(self, deployment: Any) -> dict[str, Any]:
        env_map: dict[str, Any] = {}
        for container in getattr(deployment.spec.template.spec, "containers", []) or []:
            for env in getattr(container, "env", []) or []:
                if getattr(env, "name", None):
                    env_map[env.name] = env
        return env_map

    def _env_is_mounted(self, env: Any | None) -> bool:
        if env is None:
            return False
        if getattr(env, "value", None):
            return True
        value_from = getattr(env, "value_from", None)
        return bool(value_from and getattr(value_from, "secret_key_ref", None))
