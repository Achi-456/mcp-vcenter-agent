from __future__ import annotations

import httpx

from app.websearch.base import WebSearchProviderError, WebSearchProviderTimeoutError
from app.websearch.policy import domain_from_url, source_type_for_url
from app.websearch.schemas import WebSearchRequest, WebSearchResponse, WebSearchResult


class TavilySearchProvider:
    provider_name = "tavily"

    def __init__(self, *, api_key: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        payload = {
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        if request.domains:
            payload["include_domains"] = request.domains

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise WebSearchProviderTimeoutError("Tavily search timed out.") from exc
        except Exception as exc:
            raise WebSearchProviderError("Tavily search failed.") from exc

        results = []
        for item in data.get("results", []):
            url = str(item.get("url") or "")
            if not url:
                continue
            results.append(
                WebSearchResult(
                    title=str(item.get("title") or url),
                    url=url,
                    domain=domain_from_url(url),
                    snippet=str(item.get("content") or item.get("snippet") or ""),
                    source_type=source_type_for_url(url),
                    score=item.get("score"),
                    query=request.query,
                )
            )
        return WebSearchResponse(query=request.query, results=results)
