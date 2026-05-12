from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    run_id: str
    user_message: str
    domain: str
    task_type: str
    object_type: str | None
    entity: str | None
    risk_level: str
    tool_name: str | None
    tool_endpoint: str | None
    tool_input: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    allowed: bool
    block_reason: str | None
    error_code: str | None
    selected_agent: str
    tool_response: dict[str, Any] | list[Any] | None
    tool_responses: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    validation: dict[str, Any]
    llm_enabled: bool
    llm_provider: str | None
    llm_model: str | None
    deterministic_answer: str | None
    llm_report: str | None
    llm_review: dict[str, Any] | None
    llm_used: bool
    llm_error: str | None
    final_answer_source: str
    final_answer: str
    errors: list[dict[str, Any]]
