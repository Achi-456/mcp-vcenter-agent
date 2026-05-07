from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.echo_node import echo_node
from app.graph.state import AgentState


async def load_context_node(state: AgentState) -> dict[str, object]:
    return {"turn": int(state.get("turn", 0))}


def build_graph(checkpointer: Any) -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context_node)
    graph.add_node("echo_node", echo_node)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "echo_node")
    graph.add_edge("echo_node", END)
    return graph.compile(checkpointer=checkpointer)

