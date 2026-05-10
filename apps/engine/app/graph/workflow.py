from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.clients.backend_client import BackendClient, BackendClientError
from app.graph.intent_router import intent_router_node
from app.graph.reporting import format_final_answer, summarize_tool_output, validate_state
from app.graph.safety import safety_agent_node
from app.graph.state import AgentState


def route_by_intent(state: AgentState) -> Literal["blocked_agent", "tools_agent", "vcenter_readonly_agent", "general_agent"]:
    if not state.get("allowed", True):
        return "blocked_agent"
    if state.get("task_type") in {"greeting", "unsupported"}:
        return "general_agent"
    if state.get("task_type") == "list_tools":
        return "tools_agent"
    return "vcenter_readonly_agent"


async def blocked_agent_node(state: AgentState) -> dict:
    return {
        "selected_agent": "blocked_agent",
        "findings": [{"severity": "warning", "message": state.get("block_reason") or "Request blocked."}],
    }


async def general_agent_node(state: AgentState) -> dict:
    return {"selected_agent": "general_agent", "findings": []}


async def tools_agent_node(state: AgentState) -> dict:
    return await _call_backend(state, "tools_agent")


async def vcenter_readonly_agent_node(state: AgentState) -> dict:
    return await _call_backend(state, "vcenter_readonly_agent")


async def validation_agent_node(state: AgentState) -> dict:
    return {"validation": validate_state(state)}


async def report_agent_node(state: AgentState) -> dict:
    return {"final_answer": format_final_answer(state)}


async def _call_backend(state: AgentState, selected_agent: str) -> dict:
    endpoint = state.get("tool_endpoint")
    if not endpoint:
        return {"selected_agent": selected_agent, "tool_response": None, "findings": []}
    try:
        response = await BackendClient().get(endpoint, params=state.get("tool_input") or None)
    except BackendClientError as exc:
        response = {"ok": False, "error_code": exc.error_code, "message": exc.message, "details": {}}
    return {
        "selected_agent": selected_agent,
        "tool_response": response,
        "findings": [{"severity": "info", "message": summarize_tool_output(response)}],
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("safety_agent", safety_agent_node)
    graph.add_node("blocked_agent", blocked_agent_node)
    graph.add_node("tools_agent", tools_agent_node)
    graph.add_node("vcenter_readonly_agent", vcenter_readonly_agent_node)
    graph.add_node("general_agent", general_agent_node)
    graph.add_node("validation_agent", validation_agent_node)
    graph.add_node("report_agent", report_agent_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "safety_agent")
    graph.add_conditional_edges("safety_agent", route_by_intent)
    graph.add_edge("blocked_agent", "validation_agent")
    graph.add_edge("tools_agent", "validation_agent")
    graph.add_edge("vcenter_readonly_agent", "validation_agent")
    graph.add_edge("general_agent", "validation_agent")
    graph.add_edge("validation_agent", "report_agent")
    graph.add_edge("report_agent", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
