from __future__ import annotations


def format_fallback_answer(
    intent: str,
    entity: str | None,
    tool_results: list[dict],
    blocked: bool = False,
    safety_message: str | None = None,
) -> tuple[str, str | None]:
    if blocked:
        return _format_blocked(safety_message), None

    if intent in ("get_vm_details", "get_host_details"):
        return _format_detail_answer(intent, entity, tool_results)

    if intent in ("list_tools",) and tool_results:
        tr = tool_results[0]
        data = tr.get("data", {})
        if isinstance(data, dict) and "formatted" in data:
            return data["formatted"], "I can run any read-only tool for you. Which would you like to try?"

    if intent == "search_inventory":
        return _format_search(entity, tool_results)

    return _format_generic(intent, entity, tool_results)


def _format_blocked(safety_message: str | None) -> str:
    return (
        safety_message
        or "This action is blocked for safety. Only read-only inspections are available in this phase."
    )


def _format_detail_answer(intent: str, entity: str | None, tool_results: list[dict]) -> tuple[str, str | None]:
    if not tool_results:
        msg = f"I could not find **{entity}**. No action was taken."
        return msg, "Check the exact name and try again, or ask me to list available resources."

    tr = tool_results[0]
    error_code = tr.get("error_code")
    status = tr.get("status")

    if status == "error":
        return _format_tool_error(tr, intent, entity)

    if error_code == "WRONG_OBJECT_TYPE":
        msg = tr.get("summary", f"**{entity}** looks like an ESXi host, not a VM.")
        return msg, "Try the host details tool instead, or ask me to list available resources."

    if error_code in ("VM_NOT_FOUND", "HOST_NOT_FOUND"):
        msg = tr.get("summary", f"I could not find **{entity}** in the vCenter inventory.")
        return msg, "Check the exact object name from the Inventory page, or ask me to list available resources."

    data = tr.get("data", {})

    if intent == "get_host_details":
        hosts = data.get("hosts", []) if isinstance(data, dict) else []
        if hosts:
            host = hosts[0]
            return _format_host(host, entity), _get_host_next_step()
        summary = tr.get("summary", f"I could not find **{entity}** in the vCenter inventory.")
        return summary, "Check the exact name and try again."

    if intent == "get_vm_details":
        vms = data.get("vms", []) if isinstance(data, dict) else []
        if vms:
            vm = vms[0]
            return _format_vm(vm, entity), _get_vm_next_step()
        vm = data if isinstance(data, dict) and "power_state" in data else None
        if vm:
            return _format_vm(vm, entity), _get_vm_next_step()
        summary = tr.get("summary", f"I could not find **{entity}** in the vCenter inventory.")
        return summary, "Check the exact name and try again."

    summary = tr.get("summary", "")
    if summary:
        return summary, _get_suggested_next(intent)

    return f"I could not find **{entity}**. No action was taken.", "Check the exact name and try again."


def _format_host(host: dict, name: str | None = None) -> str:
    lines = [
        f"I found ESXi host **{name or host.get('name', '?')}**. No action was taken.\n",
        "| Property | Value |",
        "|----------|-------|",
        f"| Connection State | {host.get('connection_state', 'unknown')} |",
        f"| Power State | {host.get('power_state', 'unknown')} |",
        f"| Version | {host.get('version', 'N/A')} |",
        f"| Vendor | {host.get('vendor', 'N/A')} |",
        f"| Model | {host.get('model', 'N/A')} |",
        f"| CPU Cores | {host.get('cpu_cores', 0)} |",
        f"| CPU Threads | {host.get('cpu_threads', 0)} |",
        f"| Memory | {host.get('memory_gb', 0)} GB |",
        f"| VM Count | {host.get('vm_count', 0)} |",
    ]
    if host.get("cluster"):
        lines.append(f"| Cluster | {host['cluster']} |")
    if host.get("management_ip"):
        lines.append(f"| Management IP | {host['management_ip']} |")
    return "\n".join(lines)


def _format_vm(vm: dict, name: str | None = None) -> str:
    lines = [
        f"I found **{name or vm.get('name', '?')}**. No action was taken.\n",
        "| Property | Value |",
        "|----------|-------|",
        f"| Power State | {vm.get('power_state', 'unknown')} |",
        f"| Host | {vm.get('host', 'N/A')} |",
        f"| IP Address | {vm.get('ip_address', 'N/A')} |",
        f"| Datastore | {vm.get('datastore', 'N/A')} |",
        f"| Guest OS | {vm.get('guest_os', 'N/A')} |",
        f"| CPU | {vm.get('cpu', 0)} vCPU |",
        f"| Memory | {vm.get('memory_gb', 0)} GB |",
        f"| VMware Tools | {vm.get('tools_status', 'unknown')} |",
    ]
    return "\n".join(lines)


def _format_tool_error(tr: dict, intent: str, entity: str | None) -> tuple[str, str]:
    error_code = tr.get("error_code", "UNKNOWN_ERROR")
    summary = tr.get("summary", "An unknown error occurred.")

    objective = f"Get details for {entity}" if entity else f"Execute {intent}"

    lines = [
        "I could not retrieve the requested details. No action was taken.\n",
        "**Objective:**",
        objective,
        "",
        "**What I tried:**",
        f"- Called {intent}.",
        "",
        "**Result:**",
        f"{summary} (error: {error_code})",
        "",
        "**Suggested next step:**",
        "Check the vCenter credential status in Settings, then retry the request.",
    ]
    return "\n".join(lines), "Check the vCenter credential status in Settings, then retry."


def _format_search(entity: str | None, tool_results: list[dict]) -> tuple[str, str | None]:
    if not tool_results:
        return f"No matches found for **{entity}**.", "Check the name and try again."

    tr = tool_results[0]
    data = tr.get("data", {})
    matches = data.get("matches", []) if isinstance(data, dict) else []

    if not matches:
        return f"No matches found for **{entity}**.", "Check the exact name from the Inventory page."

    lines = [f"Found {len(matches)} match(es) for **{data.get('query', entity)}**:\n"]
    for m in matches:
        lines.append(f"- **{m.get('name')}** ({m.get('type')})")

    return "\n".join(lines), "I can show details for any of these objects. Which one would you like to inspect?"


def _format_generic(intent: str, entity: str | None, tool_results: list[dict]) -> tuple[str, str | None]:
    parts = ["Here is what I found:\n"]

    for tr in tool_results:
        summary = tr.get("summary", "")
        if summary:
            parts.append(summary)

        data = tr.get("data", {})
        if isinstance(data, dict) and "overview" in data:
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
    suggested = _get_suggested_next(intent)
    return final, suggested


def _get_host_next_step() -> str:
    return "I can show VMs running on this host, check recent host events, or summarize active alarms related to it."


def _get_vm_next_step() -> str:
    return "I can also check recent events, snapshots, datastore usage, or active alarms related to this VM."


def _get_suggested_next(intent: str) -> str | None:
    suggestions = {
        "environment_overview": "I can drill down into powered-off VMs, datastore health, active alarms, or recent events.",
        "list_vms": "I can inspect any specific VM, check powered-off VMs, or show RKE2 cluster VMs.",
        "get_vm_details": "I can check recent events, datastore usage, active alarms, or snapshots for this VM.",
        "get_host_details": "I can show VMs running on this host, check recent host events, or summarize active alarms related to it.",
        "datastore_health": "I can show the full datastore list, check powered-off VMs, or review active alarms.",
        "active_alarms": "I can drill into specific alarms, check recent events, or get an environment overview.",
        "recent_events": "I can check active alarms, datastore health, or inspect any VM.",
        "rke2_vms": "I can inspect individual RKE2 VMs, check datastore health, or review active alarms.",
        "list_hosts": "I can inspect any host, check host details, or list VMs on a specific host.",
        "search_inventory": "I can search for any VM, host, datastore, network, or cluster by name.",
    }
    return suggestions.get(intent)
