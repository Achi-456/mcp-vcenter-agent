import pytest

from app.clients import backend_client
from app.graph.workflow import get_graph


@pytest.mark.asyncio
async def test_followup_it_resolves_to_previous_vm(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"], "host": "esxi01.dclab.local"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {
            "session_id": "s1",
            "run_id": "r1",
            "user_message": "what host is it on?",
            "conversation_context": {"last_entities": {"vm": "roshellevm02"}},
        }
    )
    assert calls == [("/api/v1/context/vm-details", {"name": "roshellevm02"})]
    assert state["context_resolution"]["resolved"] is True


@pytest.mark.asyncio
async def test_followup_compare_it_with_govc_resolves_previous_vm(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {
            "session_id": "s1",
            "run_id": "r1",
            "user_message": "compare it with govc",
            "conversation_context": {"last_entities": {"vm": "roshellevm02"}},
        }
    )
    assert calls == [
        ("/api/v1/context/vm-details", {"name": "roshellevm02"}),
        ("/api/v1/govc/vm-info", {"name": "roshellevm02"}),
    ]
    assert state["task_type"] == "compare_diagnostics"


@pytest.mark.asyncio
async def test_followup_missing_context_asks_clarification(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "what host is it on?", "conversation_context": {}}
    )
    assert calls == []
    assert state["task_type"] == "missing_input"
    assert "no previous session context" in state["final_answer"]


@pytest.mark.asyncio
async def test_datastore_followup_uses_previous_datastore_context(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": [{"name": "ds-critical", "status": "critical", "used_percent": 96}]}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {
            "session_id": "s1",
            "run_id": "r1",
            "user_message": "which one is most critical?",
            "conversation_context": {
                "last_intent": "inventory_summary",
                "last_tool_results_summary": [{"tool_name": "get_datastore_health"}],
            },
        }
    )
    assert calls == [("/api/v1/context/datastore-health", None)]
    assert state["task_type"] == "inventory_summary"

