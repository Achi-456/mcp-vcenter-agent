import json
import re

import httpx

from app.tools.mcp_client import execute_tool_via_mcp, get_formatted_tool_list
from app.graph.state import AgentState

# ── Intent classification ───────────────────────────────────────────────────


def _classify_intent(message: str) -> tuple[str, str | None]:
    """Classify user prompt into an intent. Returns (intent, extracted_entity)."""
    lower = message.lower().strip()

    # Extract entity name from patterns like "inspect X", "show X details", etc.
    entity = None
    for pattern in [r"get\s+details\s+for\s+(\S+)", r"inspect\s+(\S+)",
                    r"show\s+(\S+)\s+details?", r"what host is\s+(\S+)",
                    r"details?\s+(?:of|for|on)\s+(\S+)", r"info\s+(?:of|for|on)\s+(\S+)",
                    r"what\s+is\s+the\s+ip\s+of\s+(\S+)", r"datastore\s+of\s+(\S+)",
                    r"what\s+vms?\s+are\s+running\s+on\s+(\S+)"]:
        m = re.search(pattern, lower)
        if m:
            entity = m.group(1)
            break

    # Typo-tolerant risky action detection (before tool routing)
    risky_patterns = [
        r"\b(?:trun|tunr|turn|power|start|boot)\b.*\b(?:on|up)\b",
        r"\b(?:turn|power|shut)\b.*\b(?:off|down)\b",
        r"\b(?:reboot|restart|reset)\b",
        r"\b(?:delete|destroy|remove)\b.*\b(?:vm|snapshot|host)\b",
        r"\b(?:migrate|vmotion)\b",
        r"\bmaintenance\s+mode\b",
        r"\bsnapshot\s+(?:delete|revert|remove)\b",
        r"\bcreate\s+(?:vm|snapshot)\b",
        r"\brevert\b.*\bsnapshot\b",
    ]
    for pattern in risky_patterns:
        if re.search(pattern, lower):
            return ("risky_operation", entity)

    # Specific intents
    if any(w in lower for w in ["list tool", "show tool", "available tool", "what tool", "list down all the tool"]):
        return ("list_tools", None)

    if any(w in lower for w in ["environment", "overview", "summary of", "status of vcenter"]):
        return ("environment_overview", None)

    if any(w in lower for w in ["powered off", "not powered on", "power off vm", "which vms are off"]):
        return ("get_powered_off_vms", None)

    if any(w in lower for w in ["datastore health", "above 90", "critical datastore", "disk usage",
                                  "storage health", "datastore usage"]):
        return ("datastore_health", None)

    if any(w in lower for w in ["alarm", "active alarm", "triggered alarm", "alert"]):
        return ("active_alarms", None)

    if any(w in lower for w in ["recent event", "event log", "task", "show event"]):
        return ("recent_events", None)

    if any(w in lower for w in ["rke2", "kubernetes", "k8s", "cluster vm", "agentic"]):
        return ("rke2_vms", None)

    if any(w in lower for w in ["datastore", "storage"]):
        return ("list_datastores", None)

    if any(w in lower for w in ["network", "port group"]):
        return ("list_networks", None)

    if any(w in lower for w in ["cluster"]):
        return ("list_clusters", None)

    # ── Entity-based routing (host vs VM detection) ──────────────────────

    def _is_host_like(name: str) -> bool:
        """Heuristic: check if a name looks like an ESXi host, not a VM."""
        lower_n = name.lower()
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", lower_n):
            return True
        if lower_n.startswith("esxi") or lower_n.startswith("esx-") or lower_n.startswith("esx."):
            return True
        host_keywords = ["host", "esxi", "esx-", "esx.", "hypervisor", "baremetal"]
        if any(k in lower_n for k in host_keywords):
            return True
        return False

    if entity:
        if _is_host_like(entity):
            return ("get_host_details", entity)
        return ("get_vm_details", entity)

    # Keyword-based routing (no entity extracted)
    if any(w in lower for w in ["host details", "esxi details", "show host", "host info"]):
        return ("list_hosts", None)

    if any(w in lower for w in ["host", "esxi"]):
        return ("list_hosts", None)

    if any(w in lower for w in ["vm", "virtual machine"]):
        return ("list_vms", None)

    # Fallback: environment overview
    return ("environment_overview", None)


def _intent_to_tools(intent: str) -> list[str]:
    """Map an intent to the primary tool(s) to execute."""
    mapping: dict[str, list[str]] = {
        "list_tools": ["list_available_tools"],
        "environment_overview": ["get_environment_overview"],
        "list_vms": ["list_vms"],
        "list_hosts": ["list_hosts"],
        "list_datastores": ["list_datastores"],
        "list_networks": ["list_networks"],
        "list_clusters": ["list_clusters"],
        "get_vm_details": ["get_vm_details"],
        "get_host_details": ["get_host_details"],
        "datastore_health": ["get_datastore_health"],
        "active_alarms": ["get_active_alarms"],
        "recent_events": ["get_recent_events"],
        "rke2_vms": ["get_rke2_vms"],
        "get_powered_off_vms": ["get_powered_off_vms"],
    }
    return mapping.get(intent, ["get_environment_overview"])


# ── Graph nodes ──────────────────────────────────────────────────────────────


async def load_session_node(state: AgentState) -> dict[str, object]:
    return {
        "turn": int(state.get("turn", 0)) + 1,
        "status": "thinking",
    }


async def classify_request_node(state: AgentState) -> dict[str, object]:
    message = state["user_message"]
    intent, entity = _classify_intent(message)
    tools = _intent_to_tools(intent)

    if intent == "risky_operation":
        return {
            "status": "blocked",
            "safety_verdict": {
                "blocked": True,
                "risk": "approval_required",
                "reason": "HIGH_RISK_ACTION",
                "message": (
                    "This is a high-risk vCenter action and is disabled in Phase 1.4. "
                    "Power operations, deletions, snapshots, migrations, and maintenance mode "
                    "changes require approval gates planned for a future phase. "
                    "I can inspect VMs and show their current state if you'd like."
                ),
            },
        }

    return {
        "intent": intent,
        "entity": entity,
        "selected_tools": tools,
        "status": "running_tool",
    }


async def safety_check_node(state: AgentState) -> dict[str, object]:
    # Safety is now handled in classify_request_node
    # This node validates and adds context-specific safety
    intent = state.get("intent", "")
    if intent == "risky_operation":
        return {"status": "blocked"}
    return {"status": state.get("status", "running_tool")}


async def select_tools_node(state: AgentState) -> dict[str, object]:
    return {"selected_tools": state.get("selected_tools", ["get_environment_overview"])}


async def execute_tools_node(state: AgentState) -> dict[str, object]:
    tools_to_run = state.get("selected_tools", ["get_environment_overview"])
    entity = state.get("entity")
    intent = state.get("intent", "")
    results: list[dict] = []

    for tool_name in tools_to_run:
        args = {}
        if tool_name == "get_vm_details" and entity:
            args = {"name": entity}
        elif tool_name == "get_host_details" and entity:
            args = {"name": entity}
        result = await execute_tool_via_mcp(tool_name, args)
        results.append(result)

    return {"tool_results": results, "status": "streaming"}


async def generate_answer_node(state: AgentState) -> dict[str, object]:
    tool_results = state.get("tool_results", [])
    intent = state.get("intent", "")
    entity = state.get("entity")
    message = state["user_message"]

    if intent == "list_tools":
        formatted = await get_formatted_tool_list()
        return {"final_answer": formatted, "status": "done", "suggested_next": None}

    if intent == "get_vm_details" and tool_results:
        tr = tool_results[0]
        if tr.get("status") == "success":
            data = tr.get("data", {})
            vm_info = ""
            if "vms" in data and data["vms"]:
                vm = data["vms"][0]
                vm_info = _format_vm_details(vm, entity)
            elif isinstance(data, dict):
                vm_info = _format_vm_details(data, entity)
            if vm_info:
                suggested = "I can also check recent events, snapshots, datastore usage, or active alarms related to this VM."
                return {"final_answer": vm_info, "status": "done", "suggested_next": suggested}
            return {"final_answer": f"I found information for **{entity}** but could not format the details.", "status": "done", "suggested_next": None}
        return {"final_answer": f"I could not find VM **{entity}** in the vCenter inventory. Check the VM name and try again.", "status": "done", "suggested_next": None}

    # ── Host details answer ──────────────────────────────────────────────
    if intent == "get_host_details" and tool_results:
        tr = tool_results[0]
        if tr.get("status") == "success":
            data = tr.get("data", {})
            if "hosts" in data and data["hosts"]:
                host = data["hosts"][0]
                host_info = _format_host_details(host, entity)
                suggested = "I can show VMs running on this host, check recent host events, or summarize active alarms related to it."
                return {"final_answer": host_info, "status": "done", "suggested_next": suggested}
        return {"final_answer": f"I could not find host **{entity}** in the vCenter inventory.", "status": "done", "suggested_next": None}

    # ── Generic answer from tool results ─────────────────────────────────
    parts = [f"Here is what I found regarding your query:\n"]
    for tr in tool_results:
        summary = tr.get("summary", "")
        data = tr.get("data", {})

        if summary:
            parts.append(summary)

        if data and isinstance(data, dict):
            if "overview" in data:
                ov = data["overview"]
                vms = ov.get("vms", {})
                hosts = ov.get("hosts", {})
                ds = ov.get("datastores", {})
                alarms = ov.get("alarms", {})
                parts.append(f"\n- **VMs**: {vms.get('total', 0)} total ({vms.get('powered_on', 0)} on, {vms.get('powered_off', 0)} off)")
                parts.append(f"- **Hosts**: {hosts.get('total', 0)} total ({hosts.get('connected', 0)} connected)")
                parts.append(f"- **Datastores**: {ds.get('total', 0)} total ({ds.get('used_percent', 0)}% used)")
                if alarms:
                    parts.append(f"- **Alarms**: {alarms.get('total', 0)} total ({alarms.get('critical', 0)} critical)")

    final = "\n".join(parts)

    # Suggested next step
    suggested = _get_suggested_next(intent, entity)

    return {"final_answer": final, "status": "done", "suggested_next": suggested}


async def save_session_node(state: AgentState) -> dict[str, object]:
    return {}


# ── Formatting helpers ──────────────────────────────────────────────────────


def _format_vm_details(vm: dict, name: str | None = None) -> str:
    lines = [
        f"I found **{name or vm.get('name', '?')}**. No action was taken.\n",
        "| Property | Value |",
        "|----------|-------|",
        f"| **Power State** | {vm.get('power_state', 'unknown')} |",
        f"| **Host** | {vm.get('host', 'N/A')} |",
        f"| **IP Address** | {vm.get('ip_address', 'N/A')} |",
        f"| **Datastore** | {vm.get('datastore', 'N/A')} |",
        f"| **Guest OS** | {vm.get('guest_os', 'N/A')} |",
        f"| **CPU** | {vm.get('cpu', 0)} vCPU |",
        f"| **Memory** | {vm.get('memory_gb', 0)} GB |",
        f"| **VMware Tools** | {vm.get('tools_status', 'unknown')} |",
    ]
    return "\n".join(lines)


def _format_host_details(host: dict, name: str | None = None) -> str:
    lines = [
        f"I found ESXi host **{name or host.get('name', '?')}**. No action was taken.\n",
        "| Property | Value |",
        "|----------|-------|",
        f"| **Connection State** | {host.get('connection_state', 'unknown')} |",
        f"| **Power State** | {host.get('power_state', 'unknown')} |",
        f"| **Version** | {host.get('version', 'N/A')} |",
        f"| **Vendor** | {host.get('vendor', 'N/A')} |",
        f"| **Model** | {host.get('model', 'N/A')} |",
        f"| **CPU Cores** | {host.get('cpu_cores', 0)} |",
        f"| **CPU Threads** | {host.get('cpu_threads', 0)} |",
        f"| **Memory** | {host.get('memory_gb', 0)} GB |",
        f"| **VM Count** | {host.get('vm_count', 0)} |",
    ]
    return "\n".join(lines)


def _get_suggested_next(intent: str, entity: str | None) -> str | None:
    suggestions: dict[str, str] = {
        "environment_overview": "I can drill down into powered-off VMs, datastore health, active alarms, or recent events.",
        "list_vms": "I can inspect any specific VM, check powered-off VMs, or show RKE2 cluster VMs.",
        "get_vm_details": "I can check recent events, datastore usage, active alarms, or snapshots for this VM.",
        "get_host_details": "I can show VMs running on this host, check recent host events, or summarize active alarms related to it.",
        "datastore_health": "I can show the full datastore list, check powered-off VMs, or review active alarms.",
        "active_alarms": "I can drill into specific alarms, check recent events, or get an environment overview.",
        "recent_events": "I can check active alarms, datastore health, or inspect any VM.",
        "rke2_vms": "I can inspect individual RKE2 VMs, check datastore health, or review active alarms.",
    }
    return suggestions.get(intent)
