from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.graph.state import AgentState


def validate_state(state: AgentState) -> dict[str, Any]:
    errors: list[str] = []
    if state.get("object_type") == "host" and state.get("tool_name") == "get_vm_details":
        errors.append("Host request was routed to VM tool.")
    if state.get("object_type") == "vm" and state.get("tool_name") == "get_host_details":
        errors.append("VM request was routed to host tool.")
    tool_response = state.get("tool_response")
    if isinstance(tool_response, dict) and tool_response.get("ok") is False:
        errors.append(str(tool_response.get("error_code") or "BACKEND_ERROR"))
    for result in state.get("tool_responses") or []:
        response = result.get("response")
        if isinstance(response, dict) and response.get("ok") is False:
            errors.append(f"{result.get('tool_name')}: {response.get('error_code') or 'BACKEND_ERROR'}")
    return {"status": "failed" if errors else "passed", "errors": errors}


def format_final_answer(state: AgentState) -> str:
    if not state.get("allowed", True):
        return (
            f"Request blocked by safety policy: {state.get('block_reason') or state.get('error_code')}.\n\n"
            "No action was taken."
        )

    if state.get("task_type") == "greeting":
        return "Hi, I'm your vCenter Agent. How can I help you with your infrastructure today?\n\nNo action was taken."

    if state.get("task_type") == "self_description":
        return (
            "I am AgenticOps, a vCenter operations assistant for read-only infrastructure investigation.\n\n"
            "I can inspect live vCenter data for VMs, hosts, datastores, active alarms, recent events, RKE2-related VMs, "
            "and safe diagnostics through pyVmomi, govc, vSphere REST, and allowlisted MCP status tools.\n\n"
            "I am read-only by default. Future write actions such as power changes, migration, snapshot changes, or deletion "
            "must go through approval and safety checks before execution.\n\n"
            "No action was taken."
        )

    if state.get("task_type") == "model_status":
        settings = get_settings()
        model = settings.llm_model if settings.llm_model else "configuration unavailable"
        provider = settings.llm_provider if settings.llm_provider else "configuration unavailable"
        return (
            "Runtime model configuration:\n\n"
            f"| Field | Value |\n| --- | --- |\n"
            f"| LLM enabled | {settings.llm_enabled} |\n"
            f"| LLM provider | {provider} |\n"
            f"| LLM model | {model} |\n"
            f"| Final answer source | {state.get('final_answer_source', 'deterministic until final selection')} |\n\n"
            "API keys are not exposed in responses.\n\n"
            "No action was taken."
        )

    if state.get("task_type") == "general_knowledge":
        return f"{_general_knowledge_answer(str(state.get('user_message') or ''))}\n\nNo action was taken."

    if state.get("task_type") == "unsupported":
        return (
            "I can help with read-only vCenter checks such as VM details, host details, datastore "
            "health, active alarms, recent events, RKE2 VMs, govc diagnostics, vSphere REST diagnostics, "
            "and tool listing.\n\nNo action was taken."
        )

    if state.get("task_type") == "planned_v2":
        return (
            "This capability is planned for Version 2 and is not available in the current read-only agent. "
            "Version 1 can help with VM details, host details, datastore health, active alarms, recent events, "
            "govc read-only diagnostics, vSphere REST read-only diagnostics, and pyVmomi-vs-govc comparisons.\n\n"
            "No action was taken."
        )

    if state.get("task_type") == "missing_input":
        return f"{_missing_input_message(state)}\n\nNo action was taken."

    if state.get("task_type") in {"mcp_missing_input", "mcp_input_too_large", "mcp_unsupported_tool"}:
        return f"{_mcp_guidance_message(state)}\n\nNo action was taken."

    if state.get("tool_responses"):
        return _format_multi_tool_answer(state)

    tool_response = state.get("tool_response")
    if isinstance(tool_response, dict) and tool_response.get("ok") is False:
        return (
            f"Backend returned `{tool_response.get('error_code', 'ERROR')}`: "
            f"{tool_response.get('message', 'The request failed.')}.\n\nNo action was taken."
        )

    data = tool_response.get("data") if isinstance(tool_response, dict) else tool_response
    task_type = state.get("task_type")
    tool_name = state.get("tool_name")

    if task_type in {"mcp_server_info", "mcp_server_time", "mcp_echo_text"}:
        return f"{_format_mcp_status_answer(str(task_type), data)}\n\nNo action was taken."

    if tool_name in {"get_vm_details", "get_host_details"} and isinstance(data, dict):
        return f"{_dict_table(data)}\n\nNo action was taken."

    if task_type == "list_tools" and isinstance(data, list):
        rows = [
            {
                "name": item.get("name"),
                "risk": item.get("risk_level"),
                "enabled": item.get("enabled"),
                "implemented": item.get("implemented"),
            }
            for item in data[:25]
            if isinstance(item, dict)
        ]
        return f"Available tool metadata:\n\n{_list_table(rows)}\n\nNo action was taken."

    if isinstance(data, list):
        if task_type == "inventory_summary" and state.get("object_type") == "datastore":
            return f"{_format_datastore_summary(data)}\n\nNo action was taken."
        title = {
            "list_vms": "VMs",
            "list_hosts": "Hosts",
            "list_datastores": "Datastores",
            "get_datastore_health": "Datastore Health",
            "get_active_alarms": "Active Alarms",
            "get_recent_events": "Recent Events",
            "get_rke2_vms": "RKE2 VMs",
        }.get(str(tool_name), "Results")
        return f"{title}: {len(data)} item(s)\n\n{_list_table(data[:10])}\n\nNo action was taken."

    if isinstance(data, dict):
        return f"{_dict_table(data)}\n\nNo action was taken."

    return "Request completed.\n\nNo action was taken."


def _general_knowledge_answer(message: str) -> str:
    lowered = message.lower()
    note = "\n\nI can inspect your live environment if you ask for a specific VM, host, datastore, alarm, or health check."
    if "vmware tools" in lowered:
        return (
            "VMware Tools is the guest integration package installed inside a VM. It improves guest shutdown/reboot handling, "
            "time synchronization, IP and hostname reporting, quiesced snapshots, device drivers, and vCenter visibility into the guest OS."
            + note
        )
    if "vmotion" in lowered:
        return "vMotion moves a running VM from one ESXi host to another with minimal downtime, assuming shared or compatible storage, networking, and CPU compatibility are in place." + note
    if "drs" in lowered or "ha" in lowered:
        return (
            "vSphere HA restarts VMs on surviving hosts after host failure. DRS balances VM placement across hosts based on resource demand and cluster policy."
            + note
        )
    if "datastore" in lowered or "data store" in lowered:
        return "A vSphere datastore is storage presented to ESXi hosts for VM files such as VMX configuration, VMDKs, snapshots, ISOs, and logs." + note
    if "esxi" in lowered:
        return "ESXi is VMware's bare-metal hypervisor. It runs virtual machines and reports host, networking, storage, and runtime state to vCenter." + note
    return (
        "VMware vCenter is the central management plane for vSphere environments. It manages ESXi hosts, clusters, VMs, datastores, networks, alarms, events, permissions, and operational workflows such as vMotion, HA, and DRS."
        + note
    )


def _format_multi_tool_answer(state: AgentState) -> str:
    if state.get("task_type") == "health_summary":
        return _format_health_summary(state)
    if state.get("task_type") == "compare_diagnostics":
        return _format_compare_answer(state)

    rows = []
    failures = []
    for result in state.get("tool_responses") or []:
        response = result.get("response") or {}
        ok = response.get("ok", True) if isinstance(response, dict) else True
        if ok:
            data = response.get("data") if isinstance(response, dict) else response
            summary = summarize_tool_output(response)
        else:
            summary = f"{response.get('error_code')}: {response.get('message')}"
            failures.append(str(result.get("tool_name")))
        rows.append(
            {
                "source": _source_name(str(result.get("tool_name"))),
                "tool": result.get("tool_name"),
                "ok": ok,
                "summary": summary,
            }
        )
    title = "Diagnostic comparison" if state.get("task_type") == "compare_diagnostics" else "Diagnostic results"
    note = ""
    if failures:
        note = "\n\nOne or more sources returned a clean error envelope; no fallback values were invented."
    return f"{title}:\n\n{_list_table(rows)}{note}\n\nNo action was taken."


def _missing_input_message(state: AgentState) -> str:
    object_type = state.get("object_type")
    if object_type == "vm":
        return "I need a VM name. Example: `inspect VM name=roshellevm02`."
    if object_type == "host":
        return "I need an ESXi host name or host IP. Example: `check host host=esxi01.dclab.com`."
    if object_type == "tag":
        return "I need a vSphere object identifier for attached tags. Example: `show attached tags object_id=vm-123`."
    if object_type == "content_library":
        return "I need a content library identifier. Example: `show library items library_id=<library-id>`."
    return "I need a VM or host name for that read-only details request."


def _mcp_guidance_message(state: AgentState) -> str:
    if state.get("task_type") == "mcp_missing_input":
        return "I need short text to echo. Example: `echo MCP status hello`."
    if state.get("task_type") == "mcp_input_too_large":
        return "MCP safe echo accepts at most 512 characters. Please provide a shorter status string."
    return (
        "Arbitrary MCP tool execution is not supported. I can only check safe MCP status tools: "
        "server info, server time, and safe echo."
    )


def _format_mcp_status_answer(task_type: str, data: Any) -> str:
    if not isinstance(data, dict):
        return "MCP status tool returned a result, but it was not in the expected object format."
    if task_type == "mcp_server_info":
        rows = {
            "server": data.get("server"),
            "name": data.get("name"),
            "version": data.get("version"),
            "mode": data.get("mode"),
            "safe_execution": data.get("safe_execution"),
        }
        return "MCP server status:\n\n" + _dict_table(_drop_empty(rows))
    if task_type == "mcp_server_time":
        return f"MCP server UTC time: `{data.get('utc', 'not returned')}`."
    if task_type == "mcp_echo_text":
        text = str(data.get("text", ""))
        if len(text) > 120:
            text = text[:117] + "..."
        return f"MCP safe echo returned `{text}` with length `{data.get('length', len(text))}`."
    return _dict_table(data)


def _format_health_summary(state: AgentState) -> str:
    results = {str(result.get("tool_name")): result.get("response") or {} for result in state.get("tool_responses") or []}
    rows = []
    for tool_name in ("get_environment_overview", "get_datastore_health", "get_active_alarms", "get_recent_events"):
        response = results.get(tool_name, {})
        ok = response.get("ok", True) if isinstance(response, dict) else True
        rows.append(
            {
                "check": _health_label(tool_name),
                "status": "ok" if ok else "failed",
                "summary": summarize_tool_output(response),
            }
        )

    failed = [row["check"] for row in rows if row["status"] == "failed"]
    recommendation = "Review the failed source(s) first: " + ", ".join(failed) if failed else _health_recommendation(results)
    return (
        "vCenter health summary:\n\n"
        f"{_list_table(rows)}\n\n"
        f"Recommended next check: {recommendation}.\n\n"
        "No action was taken."
    )


def _format_datastore_summary(data: list[Any]) -> str:
    rows = [_datastore_row(item) for item in data if isinstance(item, dict)]
    rows = [row for row in rows if row]
    rows.sort(key=lambda row: (_datastore_status_rank(str(row.get("status", ""))), str(row.get("name") or "")))

    total = len(rows)
    critical = sum(1 for row in rows if str(row.get("status", "")).lower() == "critical")
    warning = sum(1 for row in rows if str(row.get("status", "")).lower() == "warning")
    healthy = sum(1 for row in rows if str(row.get("status", "")).lower() in {"healthy", "ok", "normal"})

    summary_rows = [
        {"metric": "total_datastores", "value": total},
        {"metric": "critical", "value": critical},
        {"metric": "warning", "value": warning},
        {"metric": "healthy", "value": healthy},
    ]
    return (
        "Datastore summary:\n\n"
        f"{_list_table(summary_rows)}\n\n"
        "Datastores:\n\n"
        f"{_list_table(rows)}"
    )


def _datastore_row(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty(
        {
            "name": item.get("name"),
            "type": item.get("type") or item.get("datastore_type"),
            "status": item.get("status"),
            "accessible": item.get("accessible"),
            "used_percent": item.get("used_percent"),
            "free_gb": item.get("free_gb"),
            "capacity_gb": item.get("capacity_gb"),
        }
    )


def _datastore_status_rank(status: str) -> int:
    return {"critical": 0, "warning": 1, "healthy": 2, "ok": 2, "normal": 2}.get(status.lower(), 3)


def _health_label(tool_name: str) -> str:
    return {
        "get_environment_overview": "environment overview",
        "get_datastore_health": "datastore health",
        "get_active_alarms": "active alarms",
        "get_recent_events": "recent events",
    }.get(tool_name, tool_name)


def _health_recommendation(results: dict[str, Any]) -> str:
    alarms = _response_data(results.get("get_active_alarms"))
    datastores = _response_data(results.get("get_datastore_health"))
    if isinstance(alarms, list) and alarms:
        return "inspect the active alarms for affected VM, host, or datastore scope"
    if isinstance(datastores, list) and any(str(item.get("status", "")).lower() in {"warning", "critical"} for item in datastores if isinstance(item, dict)):
        return "review datastore health details and free-space trends"
    return "run a focused VM or host detail check if you have a specific symptom"


def _format_compare_answer(state: AgentState) -> str:
    source_rows = []
    values_by_source: dict[str, dict[str, Any]] = {}
    for result in state.get("tool_responses") or []:
        tool_name = str(result.get("tool_name"))
        response = result.get("response") or {}
        source = _source_name(tool_name)
        ok = response.get("ok", True) if isinstance(response, dict) else True
        source_rows.append(
            {
                "source": source,
                "tool": tool_name,
                "ok": ok,
                "summary": summarize_tool_output(response),
            }
        )
        if ok:
            values_by_source[source] = _compare_fields(str(state.get("object_type") or ""), tool_name, _response_data(response))

    matched = []
    mismatched = []
    unavailable = []
    all_fields = sorted({field for fields in values_by_source.values() for field in fields})
    for field in all_fields:
        values = {source: fields.get(field) for source, fields in values_by_source.items() if fields.get(field) not in (None, "")}
        if len(values) < 2:
            unavailable.append(field)
            continue
        normalized = {source: _normalize_compare_value(value) for source, value in values.items()}
        if len(set(normalized.values())) == 1:
            matched.append({"field": field, "value": next(iter(values.values()))})
        else:
            row = {"field": field}
            row.update(values)
            mismatched.append(row)

    sections = ["Diagnostic comparison:", "", _list_table(source_rows)]
    if matched:
        sections.extend(["", "Matched fields:", "", _list_table(matched)])
    if mismatched:
        sections.extend(["", "Mismatches:", "", _list_table(mismatched)])
    if unavailable:
        sections.extend(["", "Unavailable fields:", "", ", ".join(unavailable)])
    if not matched and not mismatched:
        sections.extend(["", "No obvious comparable fields were available from both sources. No values were invented."])
    sections.extend(["", "No action was taken."])
    return "\n".join(sections)


def _compare_fields(object_type: str, tool_name: str, data: Any) -> dict[str, Any]:
    if object_type == "vm":
        return _vm_compare_fields(tool_name, data)
    if object_type == "host":
        return _host_compare_fields(tool_name, data)
    if object_type == "datastore":
        return _datastore_compare_fields(tool_name, data)
    return {}


def _vm_compare_fields(tool_name: str, data: Any) -> dict[str, Any]:
    item = _first_inventory_item(data, ("virtualMachines", "VirtualMachines", "vms", "VMs"))
    source = item if isinstance(item, dict) else data if isinstance(data, dict) else {}
    if tool_name == "get_vm_details":
        return _drop_empty(
            {
                "name": source.get("name"),
                "power state": source.get("power_state"),
                "CPU": source.get("cpu") or source.get("num_cpu"),
                "memory": source.get("memory_gb"),
                "guest OS": source.get("guest_os"),
                "datastore": source.get("datastore"),
                "host": source.get("host"),
            }
        )
    config = _dict(source.get("config"))
    hardware = _dict(config.get("hardware"))
    runtime = _dict(source.get("runtime"))
    files = _dict(config.get("files"))
    return _drop_empty(
        {
            "name": source.get("name") or source.get("Name"),
            "power state": runtime.get("powerState") or source.get("powerState"),
            "CPU": hardware.get("numCPU") or source.get("numCpu"),
            "memory": _memory_mb_to_gb(hardware.get("memoryMB")) or source.get("memory_gb"),
            "guest OS": config.get("guestFullName") or source.get("guestFullName"),
            "datastore": source.get("datastore") or files.get("vmPathName"),
            "host": source.get("host"),
        }
    )


def _host_compare_fields(tool_name: str, data: Any) -> dict[str, Any]:
    item = _first_inventory_item(data, ("hostSystems", "HostSystems", "hosts", "Hosts"))
    source = item if isinstance(item, dict) else data if isinstance(data, dict) else {}
    if tool_name == "get_host_details":
        return _drop_empty(
            {
                "name": source.get("name"),
                "connection state": source.get("connection_state"),
                "version": source.get("version"),
                "build": source.get("build"),
                "vendor": source.get("vendor"),
                "model": source.get("model"),
                "CPU": source.get("cpu_cores"),
                "memory": source.get("memory_gb"),
            }
        )
    summary = _dict(source.get("summary"))
    runtime = _dict(summary.get("runtime"))
    config = _dict(summary.get("config"))
    hardware = _dict(summary.get("hardware"))
    return _drop_empty(
        {
            "name": source.get("name") or source.get("Name"),
            "connection state": runtime.get("connectionState") or source.get("connectionState"),
            "version": config.get("product", {}).get("version") if isinstance(config.get("product"), dict) else source.get("version"),
            "build": config.get("product", {}).get("build") if isinstance(config.get("product"), dict) else source.get("build"),
            "vendor": hardware.get("vendor") or source.get("vendor"),
            "model": hardware.get("model") or source.get("model"),
            "CPU": hardware.get("numCpuCores") or source.get("cpu_cores"),
            "memory": _memory_bytes_to_gb(hardware.get("memorySize")) or source.get("memory_gb"),
        }
    )


def _datastore_compare_fields(tool_name: str, data: Any) -> dict[str, Any]:
    item = _first_inventory_item(data, ("datastores", "Datastores"))
    if item is None and isinstance(data, list) and data:
        item = data[0]
    source = item if isinstance(item, dict) else data if isinstance(data, dict) else {}
    summary = _dict(source.get("summary"))
    return _drop_empty(
        {
            "name": source.get("name") or source.get("Name") or summary.get("name"),
            "capacity": source.get("capacity_gb") or _memory_bytes_to_gb(summary.get("capacity")),
            "free": source.get("free_gb") or _memory_bytes_to_gb(summary.get("freeSpace")),
            "usage": source.get("used_percent"),
            "accessible": source.get("accessible") if "accessible" in source else summary.get("accessible"),
        }
    )


def _response_data(response: Any) -> Any:
    return response.get("data") if isinstance(response, dict) else response


def _first_inventory_item(data: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        nested = data.get("data")
        if nested is not None:
            found = _first_inventory_item(nested, keys)
            if found is not None:
                return found
        for key in keys:
            value = data.get(key)
            if isinstance(value, list) and value:
                return value[0]
            if isinstance(value, dict):
                return value
    if isinstance(data, list) and data:
        return data[0]
    return None


def _drop_empty(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "")}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _memory_mb_to_gb(value: Any) -> float | None:
    try:
        return round(float(value) / 1024, 2)
    except (TypeError, ValueError):
        return None


def _memory_bytes_to_gb(value: Any) -> float | None:
    try:
        return round(float(value) / (1024**3), 2)
    except (TypeError, ValueError):
        return None


def _normalize_compare_value(value: Any) -> str:
    return str(value).strip().lower()


def _source_name(tool_name: str) -> str:
    if tool_name.startswith("govc_"):
        return "govc"
    if tool_name.startswith("vsphere_rest_"):
        return "vSphere REST"
    if tool_name.startswith("mcp."):
        return "MCP"
    return "pyVmomi"


def summarize_tool_output(tool_response: Any) -> str:
    if isinstance(tool_response, dict) and tool_response.get("ok") is False:
        return f"{tool_response.get('error_code')}: {tool_response.get('message')}"
    data = tool_response.get("data") if isinstance(tool_response, dict) else tool_response
    if isinstance(data, list):
        return f"{len(data)} item(s) returned"
    if isinstance(data, dict):
        name = data.get("name") or data.get("status") or data.get("summary")
        return str(name or f"{len(data)} field(s) returned")
    return "Result returned"


def _dict_table(data: dict[str, Any]) -> str:
    rows = []
    for key, value in list(data.items())[:16]:
        if isinstance(value, (dict, list)):
            continue
        rows.append(f"| {key} | {value} |")
    if not rows:
        return "No displayable scalar fields returned."
    return "| Field | Value |\n| --- | --- |\n" + "\n".join(rows)


def _list_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows returned."
    if not isinstance(rows[0], dict):
        normalized = [{"value": row} for row in rows]
        return _list_table(normalized)
    columns = [key for key in rows[0].keys() if not isinstance(rows[0].get(key), (dict, list))][:8]
    if not columns:
        return "Rows returned, but no scalar fields are available for table display."
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, sep, *body])
