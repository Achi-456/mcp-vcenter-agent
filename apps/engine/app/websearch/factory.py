from __future__ import annotations

from app.core.config import Settings, get_settings
from app.websearch.base import WebSearchProvider
from app.websearch.tavily_provider import TavilySearchProvider


def create_web_search_provider(settings: Settings | None = None) -> WebSearchProvider | None:
    settings = settings or get_settings()
    if not settings.web_search_enabled:
        return None
    provider = settings.web_search_provider.strip().lower()
    if provider != "tavily":
        return None
    if not settings.tavily_api_key:
        return None
    return TavilySearchProvider(api_key=settings.tavily_api_key, timeout_seconds=settings.web_search_timeout_seconds)
