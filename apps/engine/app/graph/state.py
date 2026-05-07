from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    messages: Annotated[list[Any], add_messages]
    turn: int
    cached_result: str | None
    final_answer: str | None

