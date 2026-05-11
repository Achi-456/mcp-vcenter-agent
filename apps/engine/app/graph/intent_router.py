from __future__ import annotations

from dataclasses import dataclass

from app.graph.diagnostic_tools import compare_calls, govc_endpoint, health_summary_calls, rest_endpoint
from app.graph.entity_extraction import HOST_RE, extract_entity, extract_value
from app.graph.state import AgentState


APPROVAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("maintenance mode", "enter_maintenance_mode"),
    ("power off", "power_off_vm"),
    ("power on", "power_on_vm"),
    ("turn off", "power_off_vm"),
    ("turn on", "power_on_vm"),
    ("shutdown", "power_off_vm"),
    ("snapshot create", "create_snapshot"),
    ("create snapshot", "create_snapshot"),
    ("migrate", "migrate_vm"),
    ("change network", "change_vm_network"),
)
DESTRUCTIVE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("reboot", "reboot"),
    ("restart", "reboot"),
    ("reset", "reset"),
    ("delete", "delete_vm"),
    ("remove", "delete_vm"),
    ("destroy", "delete_vm"),
    ("kill", "kill_object"),
    ("terminate", "terminate_object"),
    ("wipe", "wipe_object"),
    ("format", "format_object"),
    ("snapshot delete", "delete_snapshot"),
    ("delete snapshot", "delete_snapshot"),
    ("snapshot revert", "revert_snapshot"),
    ("revert snapshot", "revert_snapshot"),
    ("detach", "detach_object"),
    ("attach", "attach_object"),
    ("edit", "edit_object"),
    ("update", "update_object"),
    ("patch", "patch_object"),
    ("create", "create_object"),
    ("upload", "upload_object"),
    ("copy", "copy_object"),
    ("move", "move_object"),
    ("datastore delete", "delete_datastore"),
    ("delete datastore", "delete_datastore"),
    ("unmount datastore", "unmount_datastore"),
    ("cns volume delete", "delete_cns_volume"),
    ("delete cns volume", "delete_cns_volume"),
    ("raw govc command", "raw_govc_command"),
    ("govc command", "raw_govc_command"),
    ("execute command", "execute_command"),
    ("shell command", "shell_command"),
    ("kubectl apply", "kubectl_apply"),
    ("kubectl delete", "kubectl_delete"),
    ("kubectl patch", "kubectl_patch"),
)
V2_PATTERNS = ("csi", "kubernetes", "pvc", "pv ", "persistentvolume", "govmomi", "pbm", "cns")


@dataclass(frozen=True)
class Intent:
    domain: str
    task_type: str
    object_type: str | None
    entity: str | None
    risk_level: str
    tool_name: str | None
    tool_endpoint: str | None
    tool_input: dict[str, str | int]
    tool_calls: list[dict] | None = None


def classify_intent(message: str) -> Intent:
    text = message.strip()
    lowered = text.lower()

    blocked = _classify_blocked(text, lowered)
    if blocked:
        return blocked

    if any(marker in f" {lowered} " for marker in V2_PATTERNS):
        return Intent("planned_v2", "planned_v2", None, None, "read_only", None, None, {})

    if lowered in {"hi", "hello", "hey", "hi there", "hello there"}:
        return Intent("general", "greeting", None, None, "read_only", None, None, {})

    if "list tools" in lowered or "list down all tools" in lowered or "what tools" in lowered:
        return Intent("platform", "list_tools", None, None, "read_only", "list_tools", "/api/v1/tools", {})

    if _is_health_summary(lowered):
        calls = health_summary_calls()
        return Intent("vcenter", "health_summary", None, None, "read_only", calls[0]["tool_name"], calls[0]["tool_endpoint"], {}, calls)

    compare_intent = _classify_compare(text, lowered)
    if compare_intent:
        return compare_intent

    govc_intent = _classify_govc(text, lowered)
    if govc_intent:
        return govc_intent

    rest_intent = _classify_rest(text, lowered)
    if rest_intent:
        return rest_intent

    inventory_intent = _classify_inventory(text, lowered)
    if inventory_intent:
        return inventory_intent

    details_intent = _classify_details(text, lowered)
    if details_intent:
        return details_intent

    if any(marker in lowered for marker in ("details", "detail", "inspect", "check host", "inspect vm")):
        object_type = "host" if "host" in lowered else "vm" if "vm" in lowered else None
        return Intent("vcenter", "missing_input", object_type, None, "read_only", None, None, {})

    return Intent("general", "unsupported", None, None, "read_only", None, None, {})


def _classify_blocked(message: str, lowered: str) -> Intent | None:
    entity = extract_entity(message)
    for marker, tool_name in APPROVAL_PATTERNS:
        if marker in lowered:
            return Intent("vcenter", "blocked_action", None, entity, "approval_required", tool_name, None, {})
    for marker, tool_name in DESTRUCTIVE_PATTERNS:
        if marker == "attach" and "attached tag" in lowered:
            continue
        if marker in lowered:
            return Intent("vcenter", "blocked_action", None, entity, "destructive", tool_name, None, {})
    return None


def _is_health_summary(lowered: str) -> bool:
    return (
        "vcenter health" in lowered
        or "environment health" in lowered
        or "summarize vcenter" in lowered
        or "platform health" in lowered
        or "anything wrong in vcenter" in lowered
    )


def _classify_inventory(message: str, lowered: str) -> Intent | None:
    if "datastore health" in lowered:
        return Intent("vcenter", "datastore_health", "datastore", None, "read_only", "get_datastore_health", "/api/v1/context/datastore-health", {})
    if "critical datastore" in lowered or "warning datastore" in lowered:
        return Intent("vcenter", "datastore_health", "datastore", None, "read_only", "get_datastore_health", "/api/v1/context/datastore-health", {})
    if "active alarm" in lowered or lowered.strip() == "alarms" or "show alarms" in lowered:
        return Intent("vcenter", "active_alarms", "alarm", None, "read_only", "get_active_alarms", "/api/v1/monitoring/alarms", {})
    if "recent event" in lowered or lowered.strip() == "events" or "show events" in lowered:
        return Intent("vcenter", "recent_events", "event", None, "read_only", "get_recent_events", "/api/v1/monitoring/events", {"limit": 50})
    if "rke2" in lowered:
        return Intent("vcenter", "rke2_vms", "vm", None, "read_only", "get_rke2_vms", "/api/v1/context/rke2-vms", {})
    if "list host" in lowered or "all host" in lowered or "show me all host" in lowered:
        return Intent("vcenter", "list_hosts", "host", None, "read_only", "list_hosts", "/api/v1/inventory/hosts", {})
    if "list datastore" in lowered:
        return Intent("vcenter", "list_datastores", "datastore", None, "read_only", "list_datastores", "/api/v1/inventory/datastores", {})
    if "list vm" in lowered or "all vm" in lowered or "show me all vm" in lowered or "powered off vm" in lowered or "powered-off vm" in lowered:
        return Intent("vcenter", "list_vms", "vm", None, "read_only", "list_vms", "/api/v1/inventory/vms", {})
    if "environment" in lowered or "overview" in lowered:
        return Intent("vcenter", "environment", None, None, "read_only", "get_environment_overview", "/api/v1/context/environment", {})
    return None


def _classify_details(message: str, lowered: str) -> Intent | None:
    host_entity = extract_entity(message, prefer="host")
    vm_entity = extract_entity(message, prefer="vm")
    datastore_entity = extract_entity(message, prefer="datastore")
    if "datastore" in lowered and datastore_entity:
        return Intent("vcenter", "get_details", "datastore", datastore_entity, "read_only", "list_datastores", "/api/v1/inventory/datastores", {})
    if ("host" in lowered or "esxi" in lowered or "esx-" in lowered) and host_entity:
        return Intent("vcenter", "get_details", "host", host_entity, "read_only", "get_host_details", "/api/v1/context/host-details", {"name": host_entity})
    if HOST_RE.search(message) and host_entity and ("details" in lowered or "inspect" in lowered or "check" in lowered):
        return Intent("vcenter", "get_details", "host", host_entity, "read_only", "get_host_details", "/api/v1/context/host-details", {"name": host_entity})
    if ("inspect" in lowered or "vm" in lowered or "details" in lowered or "check" in lowered or "okay" in lowered) and vm_entity:
        return Intent("vcenter", "get_details", "vm", vm_entity, "read_only", "get_vm_details", "/api/v1/context/vm-details", {"name": vm_entity})
    return None


def _intent_from_call(*, domain: str, task_type: str, object_type: str | None, entity: str | None, call: dict) -> Intent:
    return Intent(domain, task_type, object_type, entity, "read_only", call["tool_name"], call["tool_endpoint"], call.get("tool_input") or {}, [call])


def _classify_compare(message: str, lowered: str) -> Intent | None:
    if "compare" not in lowered and "validate" not in lowered:
        return None
    if "govc" not in lowered and "cli" not in lowered:
        return None
    object_type = "datastore" if "datastore" in lowered else "host" if ("host" in lowered or HOST_RE.search(message)) else "vm"
    entity = None if object_type == "datastore" else extract_entity(message, prefer=object_type)
    calls = compare_calls(object_type, entity)
    if not calls:
        return Intent("vcenter", "missing_input", object_type, entity, "read_only", None, None, {}, [])
    return Intent("vcenter", "compare_diagnostics", object_type, entity, "read_only", calls[0]["tool_name"], calls[0]["tool_endpoint"], calls[0].get("tool_input") or {}, calls)


def _classify_govc(message: str, lowered: str) -> Intent | None:
    if "govc" not in lowered and " cli " not in f" {lowered} ":
        return None
    if "volume" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_volume_ls", object_type="volume", entity=None, call=govc_endpoint("govc_volume_ls"))
    if "event" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_events", object_type="event", entity=None, call=govc_endpoint("govc_events"))
    if "datastore" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_datastore_info", object_type="datastore", entity=None, call=govc_endpoint("govc_datastore_info"))
    if "about" in lowered or "version" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_about", object_type=None, entity=None, call=govc_endpoint("govc_about"))
    if "host" in lowered or "esxi" in lowered or "esx-" in lowered or HOST_RE.search(message):
        entity = extract_entity(message, prefer="host")
        if not entity:
            return Intent("vcenter", "missing_input", "host", None, "read_only", None, None, {}, [])
        return _intent_from_call(domain="vcenter", task_type="govc_host_info", object_type="host", entity=entity, call=govc_endpoint("govc_host_info", entity))
    entity = extract_entity(message, prefer="vm")
    if "vm" in lowered or "inspect" in lowered or "verify" in lowered or entity:
        if not entity:
            return Intent("vcenter", "missing_input", "vm", None, "read_only", None, None, {}, [])
        return _intent_from_call(domain="vcenter", task_type="govc_vm_info", object_type="vm", entity=entity, call=govc_endpoint("govc_vm_info", entity))
    return _intent_from_call(domain="vcenter", task_type="govc_about", object_type=None, entity=None, call=govc_endpoint("govc_about"))


def _classify_rest(message: str, lowered: str) -> Intent | None:
    if (
        "rest" not in lowered
        and "api" not in lowered
        and "tag" not in lowered
        and "content librar" not in lowered
        and "library item" not in lowered
        and "library items" not in lowered
    ):
        return None
    object_id = extract_value(message, ("object_id", "object id", "moid"))
    library_id = extract_value(message, ("library_id", "library id"))
    if "attached" in lowered and "tag" in lowered:
        if not object_id:
            return Intent("vcenter", "missing_input", "tag", None, "read_only", None, None, {}, [])
        call = rest_endpoint("vsphere_rest_list_attached_tags", object_id)
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_attached_tags", object_type="tag", entity=object_id, call=call)
    if "library item" in lowered or ("items" in lowered and "librar" in lowered):
        if not library_id:
            return Intent("vcenter", "missing_input", "content_library", None, "read_only", None, None, {}, [])
        call = rest_endpoint("vsphere_rest_list_library_items", library_id)
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_library_items", object_type="content_library", entity=library_id, call=call)
    if "content librar" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_content_libraries", object_type="content_library", entity=None, call=rest_endpoint("vsphere_rest_list_content_libraries"))
    if "categor" in lowered and "tag" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_tag_categories", object_type="tag", entity=None, call=rest_endpoint("vsphere_rest_list_tag_categories"))
    if "tag" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_tags", object_type="tag", entity=None, call=rest_endpoint("vsphere_rest_list_tags"))
    if "task" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_recent_tasks", object_type="task", entity=None, call=rest_endpoint("vsphere_rest_list_recent_tasks"))
    if "health" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_appliance_health", object_type="appliance", entity=None, call=rest_endpoint("vsphere_rest_appliance_health"))
    if "about" in lowered or "version" in lowered:
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_about", object_type=None, entity=None, call=rest_endpoint("vsphere_rest_about"))
    return None


async def intent_router_node(state: AgentState) -> dict:
    intent = classify_intent(state["user_message"])
    return {
        "domain": intent.domain,
        "task_type": intent.task_type,
        "object_type": intent.object_type,
        "entity": intent.entity,
        "risk_level": intent.risk_level,
        "tool_name": intent.tool_name,
        "tool_endpoint": intent.tool_endpoint,
        "tool_input": intent.tool_input,
        "tool_calls": intent.tool_calls or [],
    }
