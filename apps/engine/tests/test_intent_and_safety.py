import pytest

from app.graph.intent_router import classify_intent
from app.graph.safety import safety_agent_node


def test_intent_router_classifies_host_prompt() -> None:
    intent = classify_intent("get details for esxi01.dclab.com")
    assert intent.tool_name == "get_host_details"
    assert intent.object_type == "host"
    assert intent.tool_endpoint == "/api/v1/context/host-details"


def test_intent_router_classifies_host_ip_with_context() -> None:
    intent = classify_intent("get details for host 172.25.188.21")
    assert intent.tool_name == "get_host_details"
    assert intent.entity == "172.25.188.21"


def test_intent_router_classifies_vm_prompt() -> None:
    intent = classify_intent("inspect roshellevm02")
    assert intent.tool_name == "get_vm_details"
    assert intent.object_type == "vm"
    assert intent.tool_endpoint == "/api/v1/context/vm-details"


def test_intent_router_classifies_tools_prompt() -> None:
    intent = classify_intent("list down all tools")
    assert intent.tool_name == "list_tools"
    assert intent.tool_endpoint == "/api/v1/tools"


@pytest.mark.asyncio
async def test_safety_gate_blocks_power_off() -> None:
    result = await safety_agent_node({"tool_name": "power_off_vm", "risk_level": "approval_required"})
    assert result["allowed"] is False
    assert result["error_code"] == "TOOL_REQUIRES_APPROVAL"


@pytest.mark.asyncio
async def test_safety_gate_blocks_delete() -> None:
    result = await safety_agent_node({"tool_name": "delete_vm", "risk_level": "destructive"})
    assert result["allowed"] is False
    assert result["error_code"] == "TOOL_POLICY_BLOCKED"
