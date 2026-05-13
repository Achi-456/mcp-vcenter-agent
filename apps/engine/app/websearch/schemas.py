from __future__ import annotations

from pydantic import BaseModel, Field


class WebSearchRequest(BaseModel):
    query: str
    domains: list[str] = Field(default_factory=list)
    max_results: int = 5
    official_first: bool = True


class WebSearchResult(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str
    source_type: str
    score: float | None = None
    query: str


class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult] = Field(default_factory=list)
