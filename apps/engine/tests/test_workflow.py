import pytest

from app.clients import backend_client
from app.graph.workflow import get_graph


@pytest.mark.asyncio
async def test_host_prompt_calls_host_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"], "connection_state": "connected"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "get details for esxi01.dclab.com"}
    )
    assert calls == [("/api/v1/context/host-details", {"name": "esxi01.dclab.com"})]
    assert state["validation"]["status"] == "passed"


@pytest.mark.asyncio
async def test_vm_prompt_calls_vm_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})
    assert calls == [("/api/v1/context/vm-details", {"name": "roshellevm02"})]


@pytest.mark.asyncio
async def test_datastore_health_prompt_calls_datastore_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show datastore health"})
    assert calls == [("/api/v1/context/datastore-health", None)]


@pytest.mark.asyncio
async def test_alarm_prompt_calls_alarms_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show active alarms"})
    assert calls == [("/api/v1/monitoring/alarms", None)]


@pytest.mark.asyncio
async def test_recent_events_prompt_calls_events_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show recent events"})
    assert calls == [("/api/v1/monitoring/events", {"limit": 50})]


@pytest.mark.asyncio
async def test_backend_error_creates_clean_final_answer(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": False, "error_code": "VM_NOT_FOUND", "message": "No VM found.", "details": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect missingvm"})
    assert state["validation"]["status"] == "failed"
    assert "VM_NOT_FOUND" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]


@pytest.mark.asyncio
async def test_govc_vm_prompt_calls_govc_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"VirtualMachines": [{"Name": params["name"]}]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "use govc to inspect roshellevm02"})
    assert calls == [("/api/v1/govc/vm-info", {"name": "roshellevm02"})]


@pytest.mark.asyncio
async def test_rest_tags_prompt_calls_rest_endpoint(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": ["tag-1"]}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "list REST tags"})
    assert calls == [("/api/v1/vsphere-rest/tags", None)]


@pytest.mark.asyncio
async def test_compare_vm_prompt_calls_pyvmomi_and_govc(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "compare pyVmomi and govc for roshellevm02"}
    )
    assert calls == [
        ("/api/v1/context/vm-details", {"name": "roshellevm02"}),
        ("/api/v1/govc/vm-info", {"name": "roshellevm02"}),
    ]
    assert len(state["tool_responses"]) == 2
    assert "Diagnostic comparison" in state["final_answer"]


@pytest.mark.asyncio
async def test_compare_host_prompt_calls_pyvmomi_and_govc(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"]}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "compare pyVmomi and govc for host 172.25.188.21"}
    )
    assert calls == [
        ("/api/v1/context/host-details", {"name": "172.25.188.21"}),
        ("/api/v1/govc/host-info", {"name": "172.25.188.21"}),
    ]


@pytest.mark.asyncio
async def test_rest_backend_error_creates_clean_final_answer(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": False, "error_code": "VCENTER_INVENTORY_ERROR", "message": "Provider unsupported.", "details": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show REST recent tasks"})
    assert state["validation"]["status"] == "failed"
    assert "VCENTER_INVENTORY_ERROR" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]
