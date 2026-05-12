from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.secret_store import SecretStore


class LLMModelService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def providers(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "configured": bool(self.settings.gemini_api_key),
                "models_endpoint": "/api/v1/llm/models?provider=gemini",
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "configured": bool(self.settings.openai_api_key),
                "models_endpoint": "/api/v1/llm/models?provider=openai",
            },
        ]

    def status(self) -> dict[str, Any]:
        provider = self.settings.llm_provider.strip().lower()
        configured = self._api_key(provider) is not None
        return {
            "enabled": self.settings.llm_enabled,
            "provider": provider,
            "model": self.settings.llm_model,
            "configured": configured,
            "status": "ready" if self.settings.llm_enabled and configured else "not_configured",
            "secret_source": "environment",
        }

    async def list_models(self, provider: str) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider == "gemini":
            return await self._list_gemini_models()
        if provider == "openai":
            return await self._list_openai_models()
        return {"provider": provider, "configured": False, "models": [], "error": "Unsupported provider."}

    async def _list_gemini_models(self) -> dict[str, Any]:
        api_key = self.settings.gemini_api_key
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
        api_key = self.settings.openai_api_key
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

    def _api_key(self, provider: str) -> str | None:
        if provider == "gemini":
            return self.settings.gemini_api_key
        if provider == "openai":
            return self.settings.openai_api_key
        return None

    async def configure_provider(self, provider: str, api_key: str) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider not in ["gemini", "openai"]:
            return {"configured": False, "error": f"Unsupported provider: {provider}"}

        # 1. Update secret store (Kubernetes)
        store = SecretStore()
        secret_name = "agentic-llm-provider"
        key_name = f"{provider.upper()}_API_KEY"
        
        # Read existing values to merge
        existing = await store.read_values(secret_name)
        existing[key_name] = api_key
        
        result = await store.write(secret_name, existing)
        if not result.get("written"):
            return {"configured": False, "error": result.get("reason", "Failed to write secret.")}

        # 2. Update settings in memory for current session
        if provider == "gemini":
            self.settings.gemini_api_key = api_key
        elif provider == "openai":
            self.settings.openai_api_key = api_key

        return {"configured": True, "provider": provider}
