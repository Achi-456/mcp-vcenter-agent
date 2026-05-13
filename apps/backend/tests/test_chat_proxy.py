import json

import pytest

from app.api.routes.chat import chat_stream
from app.api.routes.chat import _StreamCollector
from app.schemas.chat import ChatRequest


class FakeAgentClient:
    def __init__(self) -> None:
        self.requests = []

    async def stream_run(self, request):
        self.requests.append(request)
        yield 'data: {"type":"start","session_id":"s1","run_id":"r1"}\n\n'
        yield 'data: {"type":"final","content":"Answer","final_answer_source":"deterministic","llm_used":false}\n\n'
        yield 'data: {"type":"done"}\n\n'


class FailingAgentClient:
    async def stream_run(self, request):
        yield f"data: {json.dumps({'type': 'error', 'error_code': 'AGENT_ENGINE_UNAVAILABLE'})}\n\n"
        yield 'data: {"type":"done"}\n\n'


@pytest.mark.asyncio
async def test_chat_stream_proxies_sse_from_engine() -> None:
    response = await chat_stream(ChatRequest(message="Hi"), FakeAgentClient())
    body = ""
    async for chunk in response.body_iterator:
        body += chunk
    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert '"type":"start"' in body
    assert '"type":"final"' in body
    assert '"type":"done"' in body


@pytest.mark.asyncio
async def test_agent_run_uses_same_proxy_behavior() -> None:
    response = await chat_stream(ChatRequest(message="Hi"), FakeAgentClient())
    body = ""
    async for chunk in response.body_iterator:
        body += chunk
    assert '"type":"start"' in body
    assert '"type":"done"' in body


@pytest.mark.asyncio
async def test_engine_unavailable_streams_error_then_done() -> None:
    response = await chat_stream(ChatRequest(message="Hi"), FailingAgentClient())
    body = ""
    async for chunk in response.body_iterator:
        body += chunk
    assert "AGENT_ENGINE_UNAVAILABLE" in body
    assert '"type":"done"' in body


@pytest.mark.asyncio
async def test_stream_collector_persists_final_run_and_tool_summary() -> None:
    class FakeRepo:
        def __init__(self) -> None:
            self.calls = []

        async def start_run(self, **kwargs):
            self.calls.append(("start_run", kwargs))

        async def add_tool_call(self, **kwargs):
            self.calls.append(("add_tool_call", kwargs))

        async def add_message(self, **kwargs):
            self.calls.append(("add_message", kwargs))

        async def update_session_context(self, *args, **kwargs):
            self.calls.append(("update_session_context", args, kwargs))

        async def complete_run(self, **kwargs):
            self.calls.append(("complete_run", kwargs))

    collector = _StreamCollector(session_id="s1", user_message="inspect roshellevm02")
    collector.feed('data: {"type":"start","session_id":"s1","run_id":"r1"}\n\n')
    collector.feed('data: {"type":"intent","task_type":"get_details","object_type":"vm","entity":"roshellevm02"}\n\n')
    collector.feed('data: {"type":"tool_call","tool":"get_vm_details","risk_level":"read_only","input_summary":"name=roshellevm02"}\n\n')
    collector.feed('data: {"type":"tool_result","tool":"get_vm_details","ok":true,"output_summary":"result returned"}\n\n')
    collector.feed('data: {"type":"final","content":"Answer","final_answer_source":"deterministic","llm_used":false}\n\n')
    repo = FakeRepo()

    await collector.persist(repo)  # type: ignore[arg-type]

    names = [item[0] for item in repo.calls]
    assert names == ["start_run", "add_tool_call", "add_message", "update_session_context", "complete_run"]
    assert repo.calls[2][1]["role"] == "assistant"
    assert repo.calls[3][2]["last_entities"] == {"vm": "roshellevm02"}
