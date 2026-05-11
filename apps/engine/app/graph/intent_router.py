from __future__ import annotations

import re
from dataclasses import dataclass

from app.graph.diagnostic_tools import compare_calls, govc_endpoint, rest_endpoint
from app.graph.state import AgentState


HOST_RE = re.compile(r"\b(?:esxi[\w.-]*|esx-[\w.-]*|\d{1,3}(?:\.\d{1,3}){3})\b", re.IGNORECASE)
RISKY_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("maintenance mode", "enter_maintenance_mode", "approval_required"),
    ("power off", "power_off_vm", "approval_required"),
    ("power on", "power_on_vm", "approval_required"),
    ("shutdown", "power_off_vm", "approval_required"),
    ("reboot", "reboot", "destructive"),
    ("restart", "reboot", "destructive"),
    ("reset", "reset", "destructive"),
    ("delete", "delete_vm", "destructive"),
    ("remove", "delete_vm", "destructive"),
    ("destroy", "delete_vm", "destructive"),
    ("snapshot create", "create_snapshot", "approval_required"),
    ("create snapshot", "create_snapshot", "approval_required"),
    ("snapshot delete", "delete_snapshot", "destructive"),
    ("delete snapshot", "delete_snapshot", "destructive"),
    ("snapshot revert", "revert_snapshot", "destructive"),
    ("revert snapshot", "revert_snapshot", "destructive"),
    ("migrate", "migrate_vm", "approval_required"),
    ("change network", "change_vm_network", "approval_required"),
    ("datastore delete", "delete_datastore", "destructive"),
    ("delete datastore", "delete_datastore", "destructive"),
    ("unmount datastore", "unmount_datastore", "destructive"),
    ("cns volume delete", "delete_cns_volume", "destructive"),
    ("delete cns volume", "delete_cns_volume", "destructive"),
)


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

    for marker, tool_name, risk_level in RISKY_PATTERNS:
        if marker in lowered:
            return Intent("vcenter", "blocked_action", None, extract_entity(text), risk_level, tool_name, None, {})

    if lowered in {"hi", "hello", "hey", "hi there", "hello there"}:
        return Intent("general", "greeting", None, None, "read_only", None, None, {})

    if "list tools" in lowered or "list down all tools" in lowered or "what tools" in lowered:
        return Intent("platform", "list_tools", None, None, "read_only", "list_tools", "/api/v1/tools", {})

    compare_intent = _classify_compare(text, lowered)
    if compare_intent:
        return compare_intent

    govc_intent = _classify_govc(text, lowered)
    if govc_intent:
        return govc_intent

    rest_intent = _classify_rest(text, lowered)
    if rest_intent:
        return rest_intent

    if "datastore health" in lowered:
        return Intent(
            "vcenter",
            "datastore_health",
            "datastore",
            None,
            "read_only",
            "get_datastore_health",
            "/api/v1/context/datastore-health",
            {},
        )

    if "active alarm" in lowered or lowered.strip() == "alarms" or "show alarms" in lowered:
        return Intent(
            "vcenter",
            "active_alarms",
            "alarm",
            None,
            "read_only",
            "get_active_alarms",
            "/api/v1/monitoring/alarms",
            {},
        )

    if "recent event" in lowered or lowered.strip() == "events" or "show events" in lowered:
        return Intent(
            "vcenter",
            "recent_events",
            "event",
            None,
            "read_only",
            "get_recent_events",
            "/api/v1/monitoring/events",
            {"limit": 50},
        )

    if "rke2" in lowered:
        return Intent("vcenter", "rke2_vms", "vm", None, "read_only", "get_rke2_vms", "/api/v1/context/rke2-vms", {})

    if "list host" in lowered:
        return Intent("vcenter", "list_hosts", "host", None, "read_only", "list_hosts", "/api/v1/inventory/hosts", {})

    if "list datastore" in lowered:
        return Intent(
            "vcenter",
            "list_datastores",
            "datastore",
            None,
            "read_only",
            "list_datastores",
            "/api/v1/inventory/datastores",
            {},
        )

    if "list vm" in lowered or "powered off vm" in lowered or "powered-off vm" in lowered:
        return Intent("vcenter", "list_vms", "vm", None, "read_only", "list_vms", "/api/v1/inventory/vms", {})

    if "environment" in lowered or "overview" in lowered:
        return Intent(
            "vcenter",
            "environment",
            None,
            None,
            "read_only",
            "get_environment_overview",
            "/api/v1/context/environment",
            {},
        )

    entity = extract_entity(text)
    if ("host" in lowered or "esxi" in lowered or "esx-" in lowered or HOST_RE.search(text)) and entity:
        return Intent(
            "vcenter",
            "get_details",
            "host",
            entity,
            "read_only",
            "get_host_details",
            "/api/v1/context/host-details",
            {"name": entity},
        )

    if ("inspect" in lowered or "vm" in lowered or "details" in lowered) and entity:
        return Intent(
            "vcenter",
            "get_details",
            "vm",
            entity,
            "read_only",
            "get_vm_details",
            "/api/v1/context/vm-details",
            {"name": entity},
        )

    return Intent("general", "unsupported", None, None, "read_only", None, None, {})


def extract_entity(message: str) -> str | None:
    text = message.strip().strip("?")
    host_match = HOST_RE.search(text)
    if host_match:
        return host_match.group(0)
    patterns = (
        r"\binspect\s+([^\s,?]+)",
        r"\bdetails\s+for\s+([^\s,?]+)",
        r"\bdetail\s+for\s+([^\s,?]+)",
        r"\bfor\s+([^\s,?]+)",
        r"\babout\s+([^\s,?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _intent_from_call(
    *,
    domain: str,
    task_type: str,
    object_type: str | None,
    entity: str | None,
    call: dict,
) -> Intent:
    return Intent(
        domain,
        task_type,
        object_type,
        entity,
        "read_only",
        call["tool_name"],
        call["tool_endpoint"],
        call.get("tool_input") or {},
        [call],
    )


def _classify_compare(message: str, lowered: str) -> Intent | None:
    if "compare" not in lowered and "validate" not in lowered:
        return None
    if "govc" not in lowered and "cli" not in lowered:
        return None
    entity = extract_entity(message)
    object_type = "datastore" if "datastore" in lowered else "host" if ("host" in lowered or HOST_RE.search(message)) else "vm"
    calls = compare_calls(object_type, entity)
    if not calls:
        return Intent("vcenter", "missing_input", object_type, entity, "read_only", None, None, {}, [])
    return Intent(
        "vcenter",
        "compare_diagnostics",
        object_type,
        entity,
        "read_only",
        calls[0]["tool_name"],
        calls[0]["tool_endpoint"],
        calls[0].get("tool_input") or {},
        calls,
    )


def _classify_govc(message: str, lowered: str) -> Intent | None:
    if "govc" not in lowered and " cli " not in f" {lowered} ":
        return None
    entity = extract_entity(message)
    if "volume" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_volume_ls", object_type="volume", entity=None, call=govc_endpoint("govc_volume_ls"))
    if "event" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_events", object_type="event", entity=None, call=govc_endpoint("govc_events"))
    if "datastore" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_datastore_info", object_type="datastore", entity=None, call=govc_endpoint("govc_datastore_info"))
    if "about" in lowered or "version" in lowered:
        return _intent_from_call(domain="vcenter", task_type="govc_about", object_type=None, entity=None, call=govc_endpoint("govc_about"))
    if "host" in lowered or "esxi" in lowered or "esx-" in lowered or HOST_RE.search(message):
        if not entity:
            return Intent("vcenter", "missing_input", "host", None, "read_only", None, None, {}, [])
        return _intent_from_call(domain="vcenter", task_type="govc_host_info", object_type="host", entity=entity, call=govc_endpoint("govc_host_info", entity))
    if "vm" in lowered or "inspect" in lowered or entity:
        if not entity:
            return Intent("vcenter", "missing_input", "vm", None, "read_only", None, None, {}, [])
        return _intent_from_call(domain="vcenter", task_type="govc_vm_info", object_type="vm", entity=entity, call=govc_endpoint("govc_vm_info", entity))
    return _intent_from_call(domain="vcenter", task_type="govc_about", object_type=None, entity=None, call=govc_endpoint("govc_about"))


def _classify_rest(message: str, lowered: str) -> Intent | None:
    if "rest" not in lowered and "api" not in lowered and "tag" not in lowered and "content librar" not in lowered:
        return None
    object_id = _extract_named_value(message, ("object_id", "object id", "moid"))
    library_id = _extract_named_value(message, ("library_id", "library id"))
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
        call = rest_endpoint("vsphere_rest_list_content_libraries")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_content_libraries", object_type="content_library", entity=None, call=call)
    if "categor" in lowered and "tag" in lowered:
        call = rest_endpoint("vsphere_rest_list_tag_categories")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_tag_categories", object_type="tag", entity=None, call=call)
    if "tag" in lowered:
        call = rest_endpoint("vsphere_rest_list_tags")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_tags", object_type="tag", entity=None, call=call)
    if "task" in lowered:
        call = rest_endpoint("vsphere_rest_list_recent_tasks")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_list_recent_tasks", object_type="task", entity=None, call=call)
    if "health" in lowered:
        call = rest_endpoint("vsphere_rest_appliance_health")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_appliance_health", object_type="appliance", entity=None, call=call)
    if "about" in lowered or "version" in lowered:
        call = rest_endpoint("vsphere_rest_about")
        return _intent_from_call(domain="vcenter", task_type="vsphere_rest_about", object_type=None, entity=None, call=call)
    return None


def _extract_named_value(message: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        pattern = rf"\b{re.escape(name)}\s*[=:]?\s*([^\s,?]+)"
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1)
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
