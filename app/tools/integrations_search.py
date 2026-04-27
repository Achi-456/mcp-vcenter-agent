"""
Optional web search via Tavily API (https://tavily.com) — set TAVILY_API_KEY.
"""
from __future__ import annotations

import os
import json
import urllib.error
import urllib.request
from typing import Any


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the public web. Returns compact results (title, url, content snippet).
    Requires TAVILY_API_KEY. If missing, return a clear error for the model.
    """
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return {
            "error": "TAVILY_API_KEY is not set. Add it to the server environment to enable web search."
        }
    n = min(max(1, int(max_results or 5)), 10)
    body = json.dumps(
        {
            "api_key": key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": n,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"Tavily HTTP {e.code}", "body": e.read().decode("utf-8", errors="replace")[:500]}
    except (urllib.error.URLError, OSError) as e:
        return {"error": str(e)}

    results = data.get("results") or []
    summary = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": (r.get("content", "") or "")[:400],
        }
        for r in results
    ]
    return {"query": query, "results": summary}
