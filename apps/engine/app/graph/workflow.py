from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.workflow_nodes import (
    load_session_node,
    classify_request_node,
    safety_check_node,
    select_tools_node,
    execute_tools_node,
    prepare_llm_context_node,
    generate_llm_answer_node,
    save_session_node,
)
from app.graph.state import AgentState


def build_graph(checkpointer: Any) -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("load_session", load_session_node)
    graph.add_node("classify_request", classify_request_node)
    graph.add_node("safety_check", safety_check_node)
    graph.add_node("select_tools", select_tools_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("prepare_llm_context", prepare_llm_context_node)
    graph.add_node("generate_llm_answer", generate_llm_answer_node)
    graph.add_node("save_session", save_session_node)

    graph.add_edge(START, "load_session")
    graph.add_edge("load_session", "classify_request")

    graph.add_conditional_edges(
        "classify_request",
        lambda state: "blocked" if state.get("status") == "blocked" else "continue",
        {"blocked": "prepare_llm_context", "continue": "safety_check"},
    )

    graph.add_conditional_edges(
        "safety_check",
        lambda state: "blocked" if state.get("status") == "blocked" else "continue",
        {"blocked": "prepare_llm_context", "continue": "select_tools"},
    )

    graph.add_edge("select_tools", "execute_tools")
    graph.add_edge("execute_tools", "prepare_llm_context")
    graph.add_edge("prepare_llm_context", "generate_llm_answer")
    graph.add_edge("generate_llm_answer", "save_session")
    graph.add_edge("save_session", END)

    return graph.compile(checkpointer=checkpointer)
