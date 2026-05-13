import json

import pytest

from app.clients import backend_client
from app.main import run_agent
from app.schemas.run import RunRequest
from app.websearch import factory
from app.websearch.schemas import WebSearchRequest, WebSearchResponse, WebSearchResult


class FakeSearchProvider:
    provider_name = "fake"

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        return WebSearchResponse(
            query=request.query,
            results=[
                WebSearchResult(
                    title="Broadcom KB",
                    url="https://knowledge.broadcom.com/example",
                    domain="knowledge.broadcom.com",
                    snippet="Official guidance.",
                    source_type="official_kb",
                    score=0.9,
                    query=request.query,
                )
            ],
        )


@pytest.mark.asyncio
async def test_sse_emits_standard_sequence(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": "roshellevm02", "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    response = await run_agent(RunRequest(message="inspect roshellevm02", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [event["type"] for event in events]
    assert event_types == [
        "start",
        "intent",
        "safety_check",
        "agent_start",
        "tool_call",
        "tool_result",
        "validation",
        "final",
        "done",
    ]
    final = next(event for event in events if event["type"] == "final")
    assert final["llm_used"] is False
    assert final["final_answer_source"] == "deterministic"
    assert "llm_provider" in final
    assert "llm_model" in final
    assert "reviewer_passed" in final
    assert final["fallback_reason"] == "LLM_DISABLED"


@pytest.mark.asyncio
async def test_sse_emits_multiple_tool_events_for_compare(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    response = await run_agent(RunRequest(message="compare pyVmomi and govc for roshellevm02", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [event["type"] for event in events]
    assert event_types.count("tool_call") == 2
    assert event_types.count("tool_result") == 2
    assert event_types[-3:] == ["validation", "final", "done"]
    assert [event["tool"] for event in events if event["type"] == "tool_call"] == ["get_vm_details", "govc_vm_info"]


@pytest.mark.asyncio
async def test_sse_emits_multiple_tool_events_for_health_summary(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    response = await run_agent(RunRequest(message="summarize vCenter health", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [event["type"] for event in events]
    assert event_types.count("tool_call") == 4
    assert event_types.count("tool_result") == 4
    assert event_types[-3:] == ["validation", "final", "done"]


@pytest.mark.asyncio
async def test_sse_emits_existing_events_for_web_search(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_web_search_provider", lambda settings=None: FakeSearchProvider())
    response = await run_agent(RunRequest(message="troubleshoot datastore full issue", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert any(event["type"] == "agent_start" and event["agent"] == "web_research_agent" for event in events)
    assert any(event["type"] == "tool_call" and event["tool"] == "tavily_search" for event in events)
    assert any(event["type"] == "tool_result" and event["tool"] == "tavily_search" for event in events)


@pytest.mark.asyncio
async def test_sse_emits_standard_sequence_for_mcp_status(monkeypatch) -> None:
    async def fake_post(self, tool_name, payload=None):
        return {"ok": True, "data": {"ok": True, "server": "default", "mode": "safe"}, "metadata": {"source": "mcp"}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    response = await run_agent(RunRequest(message="test MCP", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [event["type"] for event in events]
    assert event_types == [
        "start",
        "intent",
        "safety_check",
        "agent_start",
        "tool_call",
        "tool_result",
        "validation",
        "final",
        "done",
    ]
    assert [event["tool"] for event in events if event["type"] == "tool_call"] == ["mcp.default.server_info"]


@pytest.mark.asyncio
async def test_sse_blocked_mcp_command_has_no_tool_call(monkeypatch) -> None:
    async def fake_post(self, tool_name, payload=None):
        raise AssertionError("blocked MCP command should not call backend")

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    response = await run_agent(RunRequest(message="run MCP shell command", session_id="s1"))
    body = ""
    async for chunk in response.body_iterator:
        body += chunk

    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [event["type"] for event in events]
    assert "tool_call" not in event_types
    assert "tool_result" not in event_types
    assert any(event["type"] == "safety_check" and event["allowed"] is False for event in events)
