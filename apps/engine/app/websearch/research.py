from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.graph.state import AgentState
from app.llm.schemas import redact_sensitive
from app.websearch import factory
from app.websearch.base import WebSearchProviderError
from app.websearch.policy import COMMUNITY_DOMAINS, OFFICIAL_DOMAINS, is_official_source
from app.websearch.schemas import WebSearchRequest, WebSearchResult


EXPLICIT_SEARCH_MARKERS = (
    "search vmware",
    "search broadcom",
    "look up",
    "kb",
    "knowledge base",
    "release notes",
    "official vmware guidance",
    "official broadcom guidance",
    "include official vmware",
    "using vmware docs",
)
SEARCH_TASK_TYPES = {"troubleshooting", "health_summary"}
ISSUE_MARKERS = (
    "alarm",
    "error",
    "failed",
    "failure",
    "issue",
    "problem",
    "disconnected",
    "full",
    "certificate",
    "login",
    "authentication",
    "vmotion",
    "ha",
    "drs",
    "snapshot",
    "vmware tools",
)
NO_SEARCH_TASK_TYPES = {
    "greeting",
    "self_description",
    "model_status",
    "list_tools",
    "list_vms",
    "list_hosts",
    "list_datastores",
    "get_details",
    "mcp_server_info",
    "mcp_server_time",
    "mcp_echo_text",
}


async def web_research_agent_node(state: AgentState) -> dict[str, Any]:
    settings = get_settings()
    base = {
        "web_search_enabled": settings.web_search_enabled,
        "web_search_provider": settings.web_search_provider,
        "web_search_used": False,
        "web_search_queries": [],
        "web_search_results": [],
        "web_search_error": None,
        "web_search_skipped_reason": None,
    }

    decision = should_search_web(state)
    if not decision["search"]:
        return {**base, "web_search_skipped_reason": decision["reason"]}
    if not settings.web_search_enabled:
        return {**base, "web_search_skipped_reason": "WEB_SEARCH_DISABLED"}

    provider = factory.create_web_search_provider(settings)
    if provider is None:
        reason = "WEB_SEARCH_PROVIDER_UNCONFIGURED"
        if not settings.tavily_api_key:
            reason = "TAVILY_API_KEY_MISSING"
        return {**base, "web_search_skipped_reason": reason}

    queries = build_search_queries(state)
    if not queries:
        return {**base, "web_search_skipped_reason": "NO_SEARCH_QUERY"}

    domains = list(OFFICIAL_DOMAINS)
    if _community_requested(state):
        domains.extend(COMMUNITY_DOMAINS)

    results: list[WebSearchResult] = []
    try:
        per_query_limit = max(1, min(settings.web_search_max_results, 5))
        for query in queries:
            response = await provider.search(
                WebSearchRequest(
                    query=query,
                    domains=domains,
                    max_results=per_query_limit,
                    official_first=settings.web_search_official_first,
                )
            )
            results.extend(response.results)
    except WebSearchProviderError as exc:
        return {**base, "web_search_queries": queries, "web_search_error": exc.__class__.__name__}

    normalized = _dedupe_and_rank(results, settings.web_search_max_results)
    if not normalized and not _community_requested(state):
        try:
            for query in queries[:1]:
                response = await provider.search(
                    WebSearchRequest(
                        query=query,
                        domains=list(COMMUNITY_DOMAINS),
                        max_results=max(1, settings.web_search_max_results),
                        official_first=False,
                    )
                )
                normalized = _dedupe_and_rank(response.results, settings.web_search_max_results)
                if normalized:
                    break
        except WebSearchProviderError as exc:
            return {**base, "web_search_queries": queries, "web_search_error": exc.__class__.__name__}

    return {
        **base,
        "web_search_used": bool(normalized),
        "web_search_queries": queries,
        "web_search_results": [item.model_dump() for item in normalized],
        "web_search_skipped_reason": None if normalized else "NO_WEB_RESULTS",
    }


def should_search_web(state: AgentState) -> dict[str, Any]:
    if not state.get("allowed", True):
        return {"search": False, "reason": "REQUEST_BLOCKED"}
    task_type = str(state.get("task_type") or "")
    message = str(state.get("user_message") or "").lower()
    if any(marker in message for marker in EXPLICIT_SEARCH_MARKERS):
        return {"search": True, "reason": "EXPLICIT_SEARCH_REQUEST"}
    if task_type in NO_SEARCH_TASK_TYPES:
        return {"search": False, "reason": "SIMPLE_PROMPT"}
    if task_type in SEARCH_TASK_TYPES:
        return {"search": True, "reason": "SEARCHABLE_TASK_TYPE"}
    if task_type == "general_knowledge" and any(marker in message for marker in ISSUE_MARKERS):
        return {"search": True, "reason": "GENERAL_KNOWLEDGE_WITH_ISSUE"}
    if any(marker in message for marker in ("certificate issue", "login issue", "authentication issue")):
        return {"search": True, "reason": "KNOWN_SEARCHABLE_ISSUE"}
    return {"search": False, "reason": "NOT_SEARCH_WORTHY"}


def build_search_queries(state: AgentState) -> list[str]:
    message = str(redact_sensitive(state.get("user_message") or "")).strip()
    lowered = message.lower()
    candidates: list[str] = []

    if "ha" in lowered and ("failover" in lowered or "alarm" in lowered or "failed" in lowered):
        candidates.append('"vSphere HA virtual machine failover failed" troubleshooting')
    if "datastore" in lowered or "storage" in lowered:
        candidates.append("VMware datastore full snapshot delta vmdk troubleshooting")
        candidates.append("vSphere datastore capacity alarm troubleshooting")
    if "vmware tools" in lowered:
        candidates.append("VMware Tools not running vSphere troubleshooting")
    if "vmotion" in lowered:
        candidates.append("vSphere vMotion failed troubleshooting")
    if "certificate" in lowered:
        candidates.append("vCenter certificate issue troubleshooting")
    if "login" in lowered or "authentication" in lowered:
        candidates.append("vCenter login authentication issue troubleshooting")
    if "host" in lowered and ("disconnected" in lowered or "unhealthy" in lowered):
        candidates.append("vSphere ESXi host disconnected troubleshooting")

    for result in state.get("tool_responses") or []:
        candidates.extend(_queries_from_response(result.get("response")))
    if state.get("tool_response") is not None:
        candidates.extend(_queries_from_response(state.get("tool_response")))

    if not candidates and message:
        candidates.append(f"VMware vSphere {message} troubleshooting")

    queries = []
    for candidate in candidates:
        query = " ".join(str(candidate).split())
        if query and query not in queries:
            queries.append(query)
    return queries[:3]


def _queries_from_response(response: Any) -> list[str]:
    text = str(redact_sensitive(response or "")).lower()
    queries = []
    if "vsphere ha virtual machine failover failed" in text:
        queries.append('"vSphere HA virtual machine failover failed" troubleshooting')
    if "vmware tools" in text and "not" in text:
        queries.append("VMware Tools not running vSphere troubleshooting")
    if "datastore" in text and ("critical" in text or "full" in text or "capacity" in text):
        queries.append("vSphere datastore capacity alarm troubleshooting")
    return queries


def _dedupe_and_rank(results: list[WebSearchResult], max_results: int) -> list[WebSearchResult]:
    by_url: dict[str, WebSearchResult] = {}
    for result in results:
        by_url.setdefault(result.url, result)
    ranked = sorted(
        by_url.values(),
        key=lambda item: (0 if is_official_source(item.source_type) else 1, -(item.score or 0.0), item.domain),
    )
    return ranked[:max_results]


def _community_requested(state: AgentState) -> bool:
    message = str(state.get("user_message") or "").lower()
    return "community" in message or "blog" in message
