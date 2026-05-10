import json

import pytest

from app.api.routes.chat import chat_stream
from app.schemas.chat import ChatRequest


class FakeAgentClient:
    async def stream_run(self, request):
        yield 'data: {"type":"start","session_id":"s1","run_id":"r1"}\n\n'
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
