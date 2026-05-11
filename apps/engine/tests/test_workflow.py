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


@pytest.mark.asyncio
async def test_missing_details_prompt_does_not_call_backend(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "get details"})
    assert calls == []
    assert state["task_type"] == "missing_input"
    assert "VM or host name" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]


@pytest.mark.asyncio
async def test_missing_rest_ids_do_not_call_backend(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    tags_state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show attached tags"})
    items_state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show library items"})
    assert calls == []
    assert "object_id" in tags_state["final_answer"]
    assert "library_id" in items_state["final_answer"]


@pytest.mark.asyncio
async def test_version_2_prompt_returns_guidance_without_backend_call(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "run CSI VA check"})
    assert calls == []
    assert "planned for Version 2" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]


@pytest.mark.asyncio
async def test_health_summary_calls_all_readonly_sources(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "summarize vCenter health"})
    assert calls == [
        ("/api/v1/context/environment", None),
        ("/api/v1/context/datastore-health", None),
        ("/api/v1/monitoring/alarms", None),
        ("/api/v1/monitoring/events", {"limit": 50}),
    ]
    assert "vCenter health summary" in state["final_answer"]


@pytest.mark.asyncio
async def test_health_summary_continues_when_one_source_fails(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        if endpoint == "/api/v1/monitoring/alarms":
            return {"ok": False, "error_code": "VCENTER_UNREACHABLE", "message": "Alarm source unavailable.", "details": {}}
        return {"ok": True, "data": []}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "anything wrong in vCenter?"})
    assert len(state["tool_responses"]) == 4
    assert state["validation"]["status"] == "failed"
    assert "failed source" in state["final_answer"]


@pytest.mark.asyncio
async def test_compare_datastore_prompt_calls_pyvmomi_and_govc(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": [{"name": "datastore1", "capacity_gb": 100, "free_gb": 50, "accessible": True}]}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "compare pyVmomi and govc datastore info"}
    )
    assert calls == [
        ("/api/v1/inventory/datastores", None),
        ("/api/v1/govc/datastore-info", None),
    ]
    assert "Diagnostic comparison" in state["final_answer"]
    assert "Matched fields" in state["final_answer"]


@pytest.mark.asyncio
async def test_compare_final_answer_reports_mismatches(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        if endpoint == "/api/v1/context/vm-details":
            return {"ok": True, "data": {"name": "roshellevm02", "power_state": "poweredOn", "cpu": 2}}
        return {
            "ok": True,
            "data": {"virtualMachines": [{"name": "roshellevm02", "runtime": {"powerState": "poweredOff"}, "config": {"hardware": {"numCPU": 2}}}]},
        }

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke(
        {"session_id": "s1", "run_id": "r1", "user_message": "compare pyVmomi and govc for roshellevm02"}
    )
    assert "Matched fields" in state["final_answer"]
    assert "Mismatches" in state["final_answer"]


@pytest.mark.asyncio
async def test_mcp_server_info_prompt_calls_internal_backend(monkeypatch) -> None:
    get_calls = []
    post_calls = []

    async def fake_get(self, endpoint, params=None):
        get_calls.append((endpoint, params))
        return {"ok": True, "data": {}}

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {
            "ok": True,
            "data": {"ok": True, "server": "default", "name": "test-mcp", "version": "1", "mode": "safe", "safe_execution": True},
            "metadata": {"source": "mcp", "tool": tool_name},
        }

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "test MCP"})

    assert get_calls == []
    assert post_calls == [("mcp.default.server_info", {})]
    assert "MCP server status" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]


@pytest.mark.asyncio
async def test_mcp_time_prompt_calls_internal_backend(monkeypatch) -> None:
    post_calls = []

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {"ok": True, "data": {"ok": True, "utc": "2026-05-11T00:00:00Z"}, "metadata": {"source": "mcp"}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show MCP time"})

    assert post_calls == [("mcp.default.server_time", {})]
    assert "2026-05-11T00:00:00Z" in state["final_answer"]


@pytest.mark.asyncio
async def test_mcp_echo_prompt_calls_internal_backend(monkeypatch) -> None:
    post_calls = []

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {"ok": True, "data": {"ok": True, "text": payload["text"], "length": len(payload["text"])}, "metadata": {"source": "mcp"}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "echo MCP status hello"})

    assert post_calls == [("mcp.default.echo_text", {"text": "hello"})]
    assert "length `5`" in state["final_answer"]


@pytest.mark.asyncio
async def test_large_mcp_echo_does_not_call_backend(monkeypatch) -> None:
    post_calls = []

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "echo MCP status " + ("x" * 513)})

    assert post_calls == []
    assert "512 characters" in state["final_answer"]


@pytest.mark.asyncio
async def test_arbitrary_mcp_request_does_not_call_backend(monkeypatch) -> None:
    post_calls = []

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "call MCP tool mcp.default.anything"})

    assert post_calls == []
    assert "Arbitrary MCP tool execution is not supported" in state["final_answer"]


@pytest.mark.asyncio
async def test_mcp_missing_token_returns_clean_final_answer(monkeypatch) -> None:
    async def fake_post(self, tool_name, payload=None):
        return {
            "ok": False,
            "error_code": "INTERNAL_MCP_NOT_CONFIGURED",
            "message": "Internal MCP tool access is not configured.",
            "details": {},
        }

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "is MCP server working?"})

    assert state["validation"]["status"] == "failed"
    assert "INTERNAL_MCP_NOT_CONFIGURED" in state["final_answer"]
    assert "No action was taken" in state["final_answer"]


@pytest.mark.asyncio
async def test_mcp_backend_403_returns_clean_final_answer(monkeypatch) -> None:
    async def fake_post(self, tool_name, payload=None):
        return {"ok": False, "error_code": "TOOL_POLICY_BLOCKED", "message": "Internal token invalid.", "details": {}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "show MCP server info"})

    assert "TOOL_POLICY_BLOCKED" in state["final_answer"]


@pytest.mark.asyncio
async def test_blocked_mcp_command_emits_no_tool_call_path(monkeypatch) -> None:
    post_calls = []

    async def fake_post(self, tool_name, payload=None):
        post_calls.append((tool_name, payload))
        return {"ok": True, "data": {}}

    monkeypatch.setattr(backend_client.BackendClient, "post_internal_mcp_tool", fake_post)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "execute MCP command"})

    assert post_calls == []
    assert state["allowed"] is False
    assert "No action was taken" in state["final_answer"]
