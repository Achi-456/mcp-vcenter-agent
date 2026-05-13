import pytest

from app.clients import backend_client
from app.core.config import get_settings
from app.graph.workflow import get_graph
from app.llm.schemas import build_report_writer_prompt, local_review_guard
from app.websearch import factory
from app.websearch.base import WebSearchProvider, WebSearchProviderTimeoutError
from app.websearch.research import should_search_web
from app.websearch.schemas import WebSearchRequest, WebSearchResponse, WebSearchResult


class FakeSearchProvider(WebSearchProvider):
    provider_name = "fake"

    def __init__(self, seen_requests: list[WebSearchRequest] | None = None, fail: bool = False) -> None:
        self.seen_requests = seen_requests if seen_requests is not None else []
        self.fail = fail

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        self.seen_requests.append(request)
        if self.fail:
            raise WebSearchProviderTimeoutError("timeout")
        return WebSearchResponse(
            query=request.query,
            results=[
                WebSearchResult(
                    title="Broadcom KB: vSphere HA virtual machine failover failed",
                    url="https://knowledge.broadcom.com/external/article/123456/vsphere-ha-virtual-machine-failover-failed.html",
                    domain="knowledge.broadcom.com",
                    snippet="Official guidance for HA failover failures.",
                    source_type="official_kb",
                    score=0.9,
                    query=request.query,
                ),
                WebSearchResult(
                    title="Community VMware HA notes",
                    url="https://williamlam.com/example",
                    domain="williamlam.com",
                    snippet="Community note.",
                    source_type="community_reference",
                    score=0.99,
                    query=request.query,
                ),
            ],
        )


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("WEB_SEARCH_ENABLED", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_web_search_disabled_skips_search(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "troubleshoot datastore full issue"})

    assert state["web_search_used"] is False
    assert state["web_search_skipped_reason"] == "WEB_SEARCH_DISABLED"


@pytest.mark.asyncio
async def test_missing_tavily_api_key_skips_search(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    get_settings.cache_clear()

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "troubleshoot datastore full issue"})

    assert state["web_search_used"] is False
    assert state["web_search_skipped_reason"] == "TAVILY_API_KEY_MISSING"


@pytest.mark.asyncio
async def test_troubleshooting_prompt_triggers_web_search(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()
    seen_requests: list[WebSearchRequest] = []

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_web_search_provider", lambda settings=None: FakeSearchProvider(seen_requests))

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "troubleshoot datastore full issue"})

    assert state["web_search_used"] is True
    assert seen_requests
    assert seen_requests[0].domains[0] == "knowledge.broadcom.com"
    assert state["web_search_results"][0]["source_type"] == "official_kb"


@pytest.mark.asyncio
async def test_simple_prompts_do_not_trigger_web_search(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()
    seen_requests: list[WebSearchRequest] = []

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_web_search_provider", lambda settings=None: FakeSearchProvider(seen_requests))

    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "check roshellevm02"})
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r2", "user_message": "what is your LLM model"})

    assert seen_requests == []


@pytest.mark.asyncio
async def test_explicit_kb_prompt_triggers_web_search(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()
    seen_requests: list[WebSearchRequest] = []

    monkeypatch.setattr(factory, "create_web_search_provider", lambda settings=None: FakeSearchProvider(seen_requests))

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "search VMware KB for HA failover failed"})

    assert state["web_search_used"] is True
    assert any("failover" in query.lower() for query in state["web_search_queries"])


@pytest.mark.asyncio
async def test_tavily_timeout_does_not_fail_chat(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_web_search_provider", lambda settings=None: FakeSearchProvider(fail=True))

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "troubleshoot datastore full issue"})

    assert state["web_search_used"] is False
    assert state["web_search_error"] == "WebSearchProviderTimeoutError"
    assert "No action was taken" in state["final_answer"]


def test_search_decision_skips_blocked_prompt() -> None:
    decision = should_search_web({"allowed": False, "task_type": "blocked_action", "user_message": "delete vm and search kb"})
    assert decision == {"search": False, "reason": "REQUEST_BLOCKED"}


def test_search_results_passed_to_llm_prompt() -> None:
    prompt = build_report_writer_prompt(
        {
            "user_message": "troubleshoot HA failover failed",
            "risk_level": "read_only",
            "allowed": True,
            "web_search_used": True,
            "web_search_queries": ['"vSphere HA virtual machine failover failed" troubleshooting'],
            "web_search_results": [
                {
                    "title": "Broadcom KB: HA failure",
                    "url": "https://knowledge.broadcom.com/example",
                    "domain": "knowledge.broadcom.com",
                    "snippet": "Official HA failure guidance.",
                    "source_type": "official_kb",
                }
            ],
            "deterministic_answer": "No action was taken.",
        },
        max_chars=60000,
    )

    assert "External web research" in prompt
    assert "https://knowledge.broadcom.com/example" in prompt


def test_reviewer_requires_citations_when_web_sources_used() -> None:
    issues = local_review_guard(
        "## External Knowledge\n\nOfficial guidance was reviewed.\n\n## Actions Taken\n\nNo action was taken.",
        {
            "risk_level": "read_only",
            "allowed": True,
            "web_search_results": [{"url": "https://knowledge.broadcom.com/example"}],
        },
    )

    assert "Web sources were used but URLs were not cited." in issues


def test_reviewer_accepts_cited_web_sources() -> None:
    issues = local_review_guard(
        "## External Knowledge\n\nBroadcom KB: https://knowledge.broadcom.com/example\n\n## Actions Taken\n\nNo action was taken.",
        {
            "risk_level": "read_only",
            "allowed": True,
            "web_search_results": [{"url": "https://knowledge.broadcom.com/example"}],
        },
    )

    assert issues == []
