from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiReportProvider
from app.llm.openai_provider import OpenAIReportProvider


def create_llm_provider(settings: Settings | None = None) -> LLMProvider | None:
    settings = settings or get_settings()
    if not settings.llm_enabled:
        return None

    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            return None
        return GeminiReportProvider(
            api_key=settings.gemini_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIReportProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
        )

    return None
