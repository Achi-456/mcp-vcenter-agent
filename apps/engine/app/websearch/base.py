from __future__ import annotations

from typing import Protocol

from app.websearch.schemas import WebSearchRequest, WebSearchResponse


class WebSearchProviderError(Exception):
    """Base web search provider error."""


class WebSearchProviderTimeoutError(WebSearchProviderError):
    """Raised when web search times out."""


class WebSearchProvider(Protocol):
    provider_name: str

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        ...
