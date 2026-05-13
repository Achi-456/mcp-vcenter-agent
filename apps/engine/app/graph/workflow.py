from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.clients.backend_client import BackendClient, BackendClientError
from app.graph.intent_router import intent_router_node
from app.graph.reporting import format_final_answer, summarize_tool_output, validate_state
from app.graph.safety import safety_agent_node
from app.graph.state import AgentState
from app.llm.reporting import review_llm_report, select_final_answer, write_llm_report


def route_by_intent(state: AgentState) -> Literal["blocked_agent", "tools_agent", "vcenter_readonly_agent", "general_agent"]:
    if not state.get("allowed", True):
        return "blocked_agent"
    if state.get("task_type") in {
        "greeting",
        "self_description",
        "model_status",
        "general_knowledge",
        "unsupported",
        "missing_input",
        "planned_v2",
    }:
        return "general_agent"
    if state.get("task_type") == "list_tools":
        return "tools_agent"
    if str(state.get("task_type") or "").startswith("mcp_"):
        return "vcenter_readonly_agent"
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


async def deterministic_report_agent_node(state: AgentState) -> dict:
    answer = format_final_answer(state)
    return {"deterministic_answer": answer, "final_answer": answer, "final_answer_source": "deterministic"}


async def llm_report_writer_agent_node(state: AgentState) -> dict:
    return await write_llm_report(state)


async def llm_reviewer_agent_node(state: AgentState) -> dict:
    return await review_llm_report(state)


async def final_response_selector_node(state: AgentState) -> dict:
    return await select_final_answer(state)


async def _call_backend(state: AgentState, selected_agent: str) -> dict:
    tool_calls = state.get("tool_calls") or []
    if len(tool_calls) > 1:
        responses = []
        findings = []
        for call in tool_calls:
            endpoint = call.get("tool_endpoint")
            if not endpoint:
                continue
            try:
                response = await _execute_tool_call(call)
            except BackendClientError as exc:
                response = {"ok": False, "error_code": exc.error_code, "message": exc.message, "details": {}}
            responses.append({**call, "response": response})
            findings.append({"severity": "info", "message": f"{call.get('tool_name')}: {summarize_tool_output(response)}"})
        return {
            "selected_agent": selected_agent,
            "tool_responses": responses,
            "tool_response": responses[0]["response"] if responses else None,
            "findings": findings,
        }

    endpoint = state.get("tool_endpoint")
    if not endpoint:
        return {"selected_agent": selected_agent, "tool_response": None, "findings": []}
    try:
        response = await _execute_tool_call(
            {
                "tool_name": state.get("tool_name"),
                "tool_endpoint": endpoint,
                "tool_input": state.get("tool_input") or {},
            }
        )
    except BackendClientError as exc:
        response = {"ok": False, "error_code": exc.error_code, "message": exc.message, "details": {}}
    return {
        "selected_agent": selected_agent,
        "tool_response": response,
        "findings": [{"severity": "info", "message": summarize_tool_output(response)}],
    }


async def _execute_tool_call(call: dict) -> dict:
    tool_name = str(call.get("tool_name") or "")
    endpoint = str(call.get("tool_endpoint") or "")
    tool_input = call.get("tool_input") or {}
    client = BackendClient()
    if tool_name.startswith("mcp.default."):
        return await client.post_internal_mcp_tool(tool_name, tool_input)
    return await client.get(endpoint, params=tool_input or None)


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("safety_agent", safety_agent_node)
    graph.add_node("blocked_agent", blocked_agent_node)
    graph.add_node("tools_agent", tools_agent_node)
    graph.add_node("vcenter_readonly_agent", vcenter_readonly_agent_node)
    graph.add_node("general_agent", general_agent_node)
    graph.add_node("validation_agent", validation_agent_node)
    graph.add_node("deterministic_report_agent", deterministic_report_agent_node)
    graph.add_node("llm_report_writer_agent", llm_report_writer_agent_node)
    graph.add_node("llm_reviewer_agent", llm_reviewer_agent_node)
    graph.add_node("final_response_selector", final_response_selector_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "safety_agent")
    graph.add_conditional_edges("safety_agent", route_by_intent)
    graph.add_edge("blocked_agent", "validation_agent")
    graph.add_edge("tools_agent", "validation_agent")
    graph.add_edge("vcenter_readonly_agent", "validation_agent")
    graph.add_edge("general_agent", "validation_agent")
    graph.add_edge("validation_agent", "deterministic_report_agent")
    graph.add_edge("deterministic_report_agent", "llm_report_writer_agent")
    graph.add_edge("llm_report_writer_agent", "llm_reviewer_agent")
    graph.add_edge("llm_reviewer_agent", "final_response_selector")
    graph.add_edge("final_response_selector", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
