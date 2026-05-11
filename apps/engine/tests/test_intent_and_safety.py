import pytest

from app.graph.intent_router import classify_intent
from app.graph.safety import safety_agent_node


def test_intent_router_classifies_host_prompt() -> None:
    intent = classify_intent("get details for esxi01.dclab.com")
    assert intent.tool_name == "get_host_details"
    assert intent.object_type == "host"
    assert intent.tool_endpoint == "/api/v1/context/host-details"


def test_intent_router_extracts_quoted_names() -> None:
    vm_intent = classify_intent('inspect "roshellevm02"')
    host_intent = classify_intent("get details for 'esxi01.dclab.com'")
    assert vm_intent.entity == "roshellevm02"
    assert vm_intent.tool_name == "get_vm_details"
    assert host_intent.entity == "esxi01.dclab.com"
    assert host_intent.tool_name == "get_host_details"


def test_intent_router_extracts_key_value_entities() -> None:
    assert classify_intent("inspect vm=roshellevm02").entity == "roshellevm02"
    assert classify_intent("check host=esxi01.dclab.com").entity == "esxi01.dclab.com"
    assert classify_intent("show datastore datastore=ds01 details").entity == "ds01"
    assert classify_intent("show REST attached tags object_id=vm-123").entity == "vm-123"
    assert classify_intent("show REST library items library_id=lib-1").entity == "lib-1"


def test_generic_words_are_not_entities() -> None:
    intent = classify_intent("get details")
    assert intent.task_type == "missing_input"
    assert intent.entity is None


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


def test_intent_router_classifies_govc_about() -> None:
    intent = classify_intent("govc about vcenter")
    assert intent.tool_name == "govc_about"
    assert intent.tool_endpoint == "/api/v1/govc/about"


def test_intent_router_classifies_govc_vm_info() -> None:
    intent = classify_intent("use govc to inspect roshellevm02")
    assert intent.tool_name == "govc_vm_info"
    assert intent.tool_endpoint == "/api/v1/govc/vm-info"
    assert intent.tool_input == {"name": "roshellevm02"}


def test_intent_router_classifies_govc_host_info() -> None:
    intent = classify_intent("govc host info for 172.25.188.21")
    assert intent.tool_name == "govc_host_info"
    assert intent.tool_endpoint == "/api/v1/govc/host-info"
    assert intent.tool_input == {"name": "172.25.188.21"}


def test_intent_router_classifies_govc_storage_and_events() -> None:
    assert classify_intent("show govc datastore info").tool_name == "govc_datastore_info"
    assert classify_intent("show govc events").tool_name == "govc_events"
    assert classify_intent("show govc volume list").tool_name == "govc_volume_ls"


def test_intent_router_classifies_rest_prompts() -> None:
    assert classify_intent("vSphere REST about").tool_name == "vsphere_rest_about"
    assert classify_intent("REST appliance health").tool_name == "vsphere_rest_appliance_health"
    assert classify_intent("list REST tag categories").tool_name == "vsphere_rest_list_tag_categories"
    assert classify_intent("list REST tags").tool_name == "vsphere_rest_list_tags"
    assert classify_intent("list REST content libraries").tool_name == "vsphere_rest_list_content_libraries"
    assert classify_intent("show REST recent tasks").tool_name == "vsphere_rest_list_recent_tasks"


def test_intent_router_requires_ids_for_rest_id_scoped_prompts() -> None:
    assert classify_intent("show REST attached tags").task_type == "missing_input"
    assert classify_intent("show REST library items").task_type == "missing_input"
    attached = classify_intent("show REST attached tags object_id=vm-123")
    assert attached.tool_name == "vsphere_rest_list_attached_tags"
    assert attached.tool_input == {"object_id": "vm-123"}
    items = classify_intent("show REST library items library_id=lib-1")
    assert items.tool_name == "vsphere_rest_list_library_items"
    assert items.tool_endpoint == "/api/v1/vsphere-rest/content-libraries/lib-1/items"


def test_normal_vm_details_still_uses_pyvmomi() -> None:
    intent = classify_intent("inspect roshellevm02")
    assert intent.tool_name == "get_vm_details"
    assert intent.tool_endpoint == "/api/v1/context/vm-details"


def test_host_like_prompts_route_to_host_details() -> None:
    for prompt in ("get details for host 172.25.188.21", "inspect esx-prod-01", "check esxi01.dclab.com"):
        intent = classify_intent(prompt)
        assert intent.tool_name == "get_host_details"
        assert intent.object_type == "host"


def test_intent_router_classifies_compare_prompt() -> None:
    intent = classify_intent("compare pyVmomi and govc for roshellevm02")
    assert intent.task_type == "compare_diagnostics"
    assert intent.object_type == "vm"
    assert [call["tool_name"] for call in intent.tool_calls or []] == ["get_vm_details", "govc_vm_info"]


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


def test_unsupported_version_2_prompts_do_not_select_tools() -> None:
    for prompt in ("run CSI VA check", "show Kubernetes PVCs", "use govmomi for host info", "map CNS volumes"):
        intent = classify_intent(prompt)
        assert intent.task_type == "planned_v2"
        assert intent.tool_name is None


def test_new_risky_phrases_are_blocked_before_tool_selection() -> None:
    for prompt in (
        "force delete roshellevm02",
        "simulate shell command on host",
        "kubectl apply this manifest",
        "detach network from vm",
        "patch host config",
        "raw govc command vm.power -off",
    ):
        intent = classify_intent(prompt)
        assert intent.task_type == "blocked_action"
        assert intent.tool_name is not None
