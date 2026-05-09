from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    system_prompt: str
    messages: Annotated[list[Any], add_messages]
    
    # Context settings
    provider: str
    model: str
    allow_high_risk: bool
    page_context: dict | None
    
    # Planner & Execution
    plan: dict | None
    current_step: dict | None
    risk: str | None
    approval: dict | None
    
    # Tooling
    tool_results: list[dict]
    tool_cache: dict[str, str]
    tool_version: str
    
    # Memory
    known_entities: dict
    rolling_summary: str
    turns_since_summary: int
    memory_refs: list[str]
    
    # Metrics & Status
    cost: dict
    errors: list[str]
    reflection_verdict: str | None
    reflection_nudges_used: int
    
    # Fallback / Old state compat
    final_answer: str | None
    suggested_next: str | None
    next_node: str | None
    status: str
    
    # Needed for legacy / simple loop compatibility until fully migrated
    intent: str
    entity: str | None
    safety_verdict: dict | None
    selected_tools: list[str]
    llm_context: dict | None
    answer_source: str | None
    error: str | None
