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
    intent: str
    entity: str | None
    safety_verdict: dict | None
    selected_tools: list[str]
    tool_results: list[dict]
    final_answer: str | None
    suggested_next: str | None
    llm_context: dict | None
    answer_source: str | None
    error: str | None
    status: str
