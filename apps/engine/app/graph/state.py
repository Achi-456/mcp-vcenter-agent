from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    messages: Annotated[list[Any], add_messages]
    provider: str
    model: str
    allow_high_risk: bool
    page_context: dict | None
    turn: int
    safety_verdict: dict | None
    selected_tools: list[str]
    tool_results: list[dict]
    final_answer: str | None
    error: str | None
    status: str  # thinking | running_tool | streaming | done | blocked | error
