from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.state import AgentState
from app.graph.nodes.workflow_nodes import agent_node, save_session_node
from app.tools.registry import get_langchain_tools

def build_graph(checkpointer: Any) -> Any:
    graph = StateGraph(AgentState)
    
    tools = get_langchain_tools()
    
    # Initialize the ToolNode with our mapped tools
    tool_node = ToolNode(tools) if tools else None

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("save_session", save_session_node)
    if tool_node:
        graph.add_node("tools", tool_node)

    # Add edges
    graph.add_edge(START, "agent")
    
    if tool_node:
        # Standard tool calling loop
        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", "__end__": "save_session"},
        )
        graph.add_edge("tools", "agent")
    else:
        # If no tools available, go straight to save
        graph.add_edge("agent", "save_session")
        
    graph.add_edge("save_session", END)

    return graph.compile(checkpointer=checkpointer)
