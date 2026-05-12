from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.graph.state import AgentState
from app.llm.prompts import REPORT_WRITER_USER_TEMPLATE, REVIEWER_USER_TEMPLATE

SECRET_MARKERS = (
    "password",
    "token",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "internal_tool_api_token",
)
MAX_ARRAY_ITEMS = 5


class LLMReview(BaseModel):
    passed: bool = False
    safe_to_return: bool = False
    issues: list[str] = Field(default_factory=list)
    fallback_required: bool = True


def build_report_writer_prompt(state: AgentState, *, max_chars: int) -> str:
    package = build_evidence_package(state)
    prompt = REPORT_WRITER_USER_TEMPLATE.format(
        user_message=str(state.get("user_message") or ""),
        intent_json=_json(package["intent"]),
        safety_json=_json(package["safety"]),
        tool_calls_json=_json(package["tool_calls"]),
        tool_results_json=_json(package["tool_results"]),
        deterministic_answer=str(state.get("deterministic_answer") or ""),
    )
    return truncate_text(prompt, max_chars)


def build_reviewer_prompt(state: AgentState, llm_report: str, *, max_chars: int) -> str:
    package = build_evidence_package(state)
    prompt = REVIEWER_USER_TEMPLATE.format(
        evidence_json=_json(package),
        llm_report=truncate_text(llm_report, max_chars // 2),
    )
    return truncate_text(prompt, max_chars)


def build_evidence_package(state: AgentState) -> dict[str, Any]:
    return redact_sensitive(
        {
            "user_message": state.get("user_message"),
            "intent": {
                "domain": state.get("domain"),
                "task_type": state.get("task_type"),
                "object_type": state.get("object_type"),
                "entity": state.get("entity"),
                "tool_name": state.get("tool_name"),
                "tool_endpoint": state.get("tool_endpoint"),
                "tool_input": state.get("tool_input") or {},
            },
            "safety": {
                "risk_level": state.get("risk_level", "read_only"),
                "allowed": state.get("allowed", True),
                "error_code": state.get("error_code"),
                "block_reason": state.get("block_reason"),
            },
            "tool_calls": _tool_calls(state),
            "tool_results": _tool_results(state),
            "deterministic_answer": state.get("deterministic_answer"),
            "allowed_actions": "read-only only",
        }
    )


def parse_review_json(text: str) -> LLMReview:
    try:
        start = text.find("{")
        end = text.rfind("}")
        raw = text[start : end + 1] if start >= 0 and end >= start else text
        return LLMReview.model_validate_json(raw)
    except Exception:
        return LLMReview(
            passed=False,
            safe_to_return=False,
            issues=["Reviewer returned invalid JSON."],
            fallback_required=True,
        )


def local_review_guard(report: str, state: AgentState) -> list[str]:
    issues: list[str] = []
    lowered = report.lower()
    if state.get("allowed", True) and state.get("risk_level", "read_only") == "read_only" and "no action was taken." not in lowered:
        issues.append("Missing required read-only action statement.")
    if any(marker in lowered for marker in ("api_key", "authorization:", "bearer ", "cookie:", "password=", "token=")):
        issues.append("Possible secret-bearing text present.")
    if any(marker in lowered for marker in ("delete the", "run rm", "kubectl delete", "power off", "format datastore")) and "approval" not in lowered:
        issues.append("Unsafe recommendation without approval language.")
    return issues


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if _is_secret_key(str(key)):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive(item)
        return result
    if isinstance(value, list):
        redacted = [redact_sensitive(item) for item in value[:MAX_ARRAY_ITEMS]]
        if len(value) > MAX_ARRAY_ITEMS:
            redacted.append({"truncated": True, "total_items": len(value)})
        return redacted
    return value


def truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 80] + "\n\n[TRUNCATED: evidence exceeded input limit]"


def _tool_calls(state: AgentState) -> list[dict[str, Any]]:
    calls = state.get("tool_calls") or []
    if calls:
        return [
            {
                "tool_name": call.get("tool_name"),
                "tool_endpoint": call.get("tool_endpoint"),
                "tool_input": call.get("tool_input") or {},
            }
            for call in calls
        ]
    if state.get("tool_name"):
        return [
            {
                "tool_name": state.get("tool_name"),
                "tool_endpoint": state.get("tool_endpoint"),
                "tool_input": state.get("tool_input") or {},
            }
        ]
    return []


def _tool_results(state: AgentState) -> list[dict[str, Any]]:
    responses = state.get("tool_responses") or []
    if responses:
        return [
            {
                "tool_name": item.get("tool_name"),
                "response": _summarize_response(item.get("response")),
            }
            for item in responses
        ]
    if state.get("tool_response") is not None:
        return [{"tool_name": state.get("tool_name"), "response": _summarize_response(state.get("tool_response"))}]
    return []


def _summarize_response(response: Any) -> Any:
    if isinstance(response, dict):
        data = response.get("data")
        summary = {key: redact_sensitive(value) for key, value in response.items() if key != "data"}
        summary["data"] = _summarize_data(data)
        return summary
    return _summarize_data(response)


def _summarize_data(data: Any) -> Any:
    if isinstance(data, list):
        return {
            "type": "list",
            "count": len(data),
            "items": redact_sensitive(data),
        }
    if isinstance(data, dict):
        return redact_sensitive(data)
    return data


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_MARKERS)


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)
