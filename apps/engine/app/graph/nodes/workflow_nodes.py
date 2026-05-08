import json
import asyncio

import httpx

from app.tools.registry import get_all_tools, FASTAPI_INTERNAL
from app.graph.state import AgentState


async def load_session_node(state: AgentState) -> dict[str, object]:
    return {
        "turn": int(state.get("turn", 0)) + 1,
        "status": "thinking",
    }


async def safety_check_node(state: AgentState) -> dict[str, object]:
    from app.safety.classifier import classify_safety

    verdict = classify_safety(state["user_message"])
    if verdict["blocked"]:
        return {
            "safety_verdict": verdict,
            "status": "blocked",
        }
    return {
        "safety_verdict": verdict,
        "status": "running_tool",
    }


async def select_tools_node(state: AgentState) -> dict[str, object]:
    user_message = state["user_message"].lower()
    tools = get_all_tools()
    selected: list[str] = []

    tool_keywords = {
        "get_environment_overview": ["environment", "overview", "summary", "status of vcenter"],
        "list_vms": ["list vm", "show vm", "virtual machine", "all vm"],
        "list_hosts": ["list host", "show host", "esxi"],
        "list_clusters": ["cluster", "show cluster"],
        "list_datastores": ["datastore", "show datastore", "storage"],
        "list_networks": ["network", "port group", "show network"],
        "get_powered_off_vms": ["powered off", "power off vm", "not powered on"],
        "get_datastore_health": ["datastore health", "critical datastore", "above 90", "disk usage"],
        "get_active_alarms": ["alarm", "active alarm", "triggered alarm"],
        "get_recent_events": ["recent event", "event log", "show event"],
        "get_rke2_vms": ["rke2", "kubernetes", "cluster vm", "k8s"],
    }

    for tool in tools:
        if tool.risk != "read_only":
            continue
        for keyword in tool_keywords.get(tool.name, []):
            if keyword in user_message:
                if tool.name not in selected:
                    selected.append(tool.name)
                break

    if not selected:
        selected = ["get_environment_overview"]

    return {"selected_tools": selected}


async def execute_tools_node(state: AgentState) -> dict[str, object]:
    tools_to_run = state.get("selected_tools", ["get_environment_overview"])
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for tool_name in tools_to_run:
            from app.tools.registry import get_tool
            tool = get_tool(tool_name)
            if not tool:
                results.append({"tool": tool_name, "status": "error", "summary": "Tool not found"})
                continue
            try:
                resp = await client.get(tool.api_endpoint)
                if resp.status_code == 200:
                    data = resp.json()
                    summary = data.get("summary", "") or str(data.get("count", ""))
                    results.append({"tool": tool_name, "status": "success", "data": data, "summary": summary})
                else:
                    results.append({"tool": tool_name, "status": "error", "summary": f"HTTP {resp.status_code}"})
            except Exception as exc:
                results.append({"tool": tool_name, "status": "error", "summary": str(exc)[:100]})

    return {"tool_results": results, "status": "streaming"}


async def generate_answer_node(state: AgentState) -> dict[str, object]:
    tool_results = state.get("tool_results", [])
    user_message = state["user_message"]

    parts = [f"Answering: {user_message}\n"]
    for tr in tool_results:
        tool_name = tr.get("tool", "unknown")
        status = tr.get("status", "error")
        summary = tr.get("summary", "")
        data = tr.get("data", {})

        parts.append(f"\nTool: {tool_name} ({status})")

        if status == "success" and data:
            if "vms" in data and isinstance(data["vms"], list):
                parts.append(f"  Found {len(data['vms'])} VMs")
                for vm in data["vms"][:5]:
                    parts.append(f"  - {vm.get('name', '?')} [{vm.get('power_state', '?')}]")
            elif "items" in data:
                parts.append(f"  Found {data.get('count', len(data['items']))} items")
            elif "overview" in data:
                ov = data["overview"]
                vms = ov.get("vms", {})
                hosts = ov.get("hosts", {})
                ds = ov.get("datastores", {})
                parts.append(f"  VMs: {vms.get('total', 0)} total, {vms.get('powered_on', 0)} on, {vms.get('powered_off', 0)} off")
                parts.append(f"  Hosts: {hosts.get('total', 0)} total, {hosts.get('connected', 0)} connected")
                parts.append(f"  Datastores: {ds.get('total', 0)} total, {ds.get('used_percent', 0)}% used")
            if summary:
                parts.append(f"  {summary}")

    final = "\n".join(parts)
    return {"final_answer": final, "status": "done"}


async def save_session_node(state: AgentState) -> dict[str, object]:
    return {}
