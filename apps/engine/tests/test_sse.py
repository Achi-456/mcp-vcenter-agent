import json

import pytest

from app.clients import backend_client
from app.main import run_agent
from app.schemas.run import RunRequest


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
