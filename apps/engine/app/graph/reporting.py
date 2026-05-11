from __future__ import annotations

from typing import Any

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

    if state.get("task_type") == "unsupported":
        return (
            "I can help with read-only vCenter checks such as VM details, host details, datastore "
            "health, active alarms, recent events, RKE2 VMs, govc diagnostics, vSphere REST diagnostics, "
            "and tool listing.\n\nNo action was taken."
        )

    if state.get("task_type") == "missing_input":
        return (
            "I need a specific identifier for that read-only diagnostic request. For attached tags, provide "
            "`object_id=<moid>`. For library items, provide `library_id=<id>`.\n\nNo action was taken."
        )

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


def _format_multi_tool_answer(state: AgentState) -> str:
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


def _source_name(tool_name: str) -> str:
    if tool_name.startswith("govc_"):
        return "govc"
    if tool_name.startswith("vsphere_rest_"):
        return "vSphere REST"
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
    columns = [key for key in rows[0].keys() if not isinstance(rows[0].get(key), (dict, list))][:6]
    if not columns:
        return "Rows returned, but no scalar fields are available for table display."
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, sep, *body])
