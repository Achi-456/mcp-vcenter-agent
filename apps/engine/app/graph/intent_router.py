from __future__ import annotations

import re
from dataclasses import dataclass

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
        r"\babout\s+([^\s,?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
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
    }
