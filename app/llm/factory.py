"""Provider factory."""
from __future__ import annotations

import os
from typing import Iterator

from app.llm.base import LLMProvider, NormalizedMessage, StepResult
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.openai_provider import OpenAIProvider, GrokProvider, KimiProvider
from app.llm.gemini_provider import GeminiProvider


_INSTANCES: dict[str, LLMProvider] = {}


def clear_provider_cache() -> None:
    """Drop cached provider instances so new API keys from the environment take effect."""
    _INSTANCES.clear()


def _get_or_create(name: str) -> LLMProvider:
    if name in _INSTANCES:
        return _INSTANCES[name]
    if name == "anthropic":
        inst: LLMProvider = AnthropicProvider()
    elif name == "openai":
        inst = OpenAIProvider()
    elif name == "grok":
        inst = GrokProvider()
    elif name == "kimi":
        inst = KimiProvider()
    elif name == "gemini":
        inst = GeminiProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")
    _INSTANCES[name] = inst
    return inst


class FailoverProvider:
    """Wraps a primary LLMProvider; on retry exhaustion (RuntimeError) or 5xx, delegates to fallback.

    Once the fallback is activated for a session it stays active for the remainder of that session
    so that the conversation context remains consistent.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self._using_fallback = False

    # ── LLMProvider protocol attributes ──────────────────────────────────

    @property
    def name(self) -> str:
        return self._fallback.name if self._using_fallback else self._primary.name

    @property
    def env_key(self) -> str:
        return self._fallback.env_key if self._using_fallback else self._primary.env_key

    @property
    def default_model(self) -> str:
        return self._fallback.default_model if self._using_fallback else self._primary.default_model

    def is_configured(self) -> bool:
        return self._primary.is_configured()

    def list_models(self) -> list[dict]:
        return self._primary.list_models()

    # ── Streaming step with automatic failover ────────────────────────────

    def stream_step(
        self,
        *,
        system: str,
        messages: list[NormalizedMessage],
        tools: list[dict],
        model: str,
        max_tokens: int,
    ) -> Iterator[dict]:
        kwargs = dict(
            system=system,
            messages=messages,
            tools=tools,
            model=model,
            max_tokens=max_tokens,
        )

        if self._using_fallback:
            yield from self._fallback.stream_step(**kwargs)
            return

        # Attempt primary; on retry exhaustion switch to fallback.
        primary_gen = self._primary.stream_step(**kwargs)
        try:
            yield from primary_gen
        except RuntimeError as exc:
            self._using_fallback = True
            yield {
                "type": "text",
                "content": (
                    f"\n\n[Rate limit exhausted on {self._primary.name} — "
                    f"switching to fallback provider: {self._fallback.name}]\n\n"
                ),
            }
            # Retry the same turn from the beginning on the fallback.
            yield from self._fallback.stream_step(**kwargs)


PROVIDERS: list[dict] = [
    {"id": "anthropic", "label": "Anthropic (Claude)"},
    {"id": "openai", "label": "OpenAI (GPT)"},
    {"id": "kimi", "label": "Kimi (Moonshot)"},
    {"id": "gemini", "label": "Google Gemini"},
    {"id": "grok", "label": "xAI Grok"},
]


def get_provider(name: str) -> LLMProvider:
    """Return the provider for *name*, wrapping it with FailoverProvider when AGENT_FALLBACK_PROVIDER is set."""
    primary = _get_or_create(name)
    fallback_name = os.environ.get("AGENT_FALLBACK_PROVIDER", "").strip().lower()
    if fallback_name and fallback_name != name:
        fallback = _get_or_create(fallback_name)
        return FailoverProvider(primary, fallback)
    return primary


def list_configured_providers() -> list[dict]:
    """Return PROVIDERS annotated with 'configured' flag and default_model."""
    out = []
    for p in PROVIDERS:
        inst = _get_or_create(p["id"])
        out.append(
            {
                "id": p["id"],
                "label": p["label"],
                "configured": inst.is_configured(),
                "default_model": inst.default_model,
            }
        )
    return out
