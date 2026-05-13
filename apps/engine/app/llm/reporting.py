from __future__ import annotations

from app.core.config import get_settings
from app.graph.state import AgentState
from app.llm import factory
from app.llm.base import LLMMessage, LLMProviderError
from app.llm.prompts import REPORT_WRITER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT
from app.llm.schemas import (
    LLMReview,
    build_report_writer_prompt,
    build_reviewer_prompt,
    local_review_guard,
    parse_review_json,
)


async def write_llm_report(state: AgentState) -> dict:
    settings = get_settings()
    base = {
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_used": False,
        "llm_report": None,
        "llm_error": None,
    }
    if not settings.llm_enabled:
        return {**base, "llm_error": "LLM_DISABLED"}
    if not settings.llm_report_writer_enabled:
        return {**base, "llm_error": "LLM_REPORT_WRITER_DISABLED"}
    if not state.get("allowed", True):
        return {**base, "llm_error": "LLM_SKIPPED_FOR_BLOCKED_REQUEST"}

    provider = factory.create_llm_provider(settings)
    if provider is None:
        return {**base, "llm_error": "LLM_PROVIDER_UNCONFIGURED"}

    prompt = build_report_writer_prompt(state, max_chars=settings.llm_max_input_chars)
    try:
        report = await provider.complete(
            [
                LLMMessage(role="system", content=REPORT_WRITER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ]
        )
    except LLMProviderError as exc:
        return {**base, "llm_error": exc.__class__.__name__}

    if not report.strip():
        return {**base, "llm_error": "LLM_EMPTY_REPORT"}
    return {**base, "llm_report": report.strip()}


async def review_llm_report(state: AgentState) -> dict:
    report = state.get("llm_report")
    if not report:
        return {"llm_review": None}

    settings = get_settings()
    local_issues = local_review_guard(str(report), state)
    if local_issues:
        return {
            "llm_review": LLMReview(
                passed=False,
                safe_to_return=False,
                issues=local_issues,
                fallback_required=True,
            ).model_dump(),
            "llm_error": "LLM_LOCAL_REVIEW_FAILED",
        }

    if not settings.llm_reviewer_enabled:
        return {
            "llm_review": LLMReview(
                passed=True,
                safe_to_return=True,
                issues=[],
                fallback_required=False,
            ).model_dump(),
        }

    provider = factory.create_llm_provider(settings)
    if provider is None:
        return {
            "llm_review": LLMReview(
                passed=False,
                safe_to_return=False,
                issues=["LLM reviewer provider is not configured."],
                fallback_required=True,
            ).model_dump(),
            "llm_error": "LLM_REVIEWER_UNCONFIGURED",
        }

    prompt = build_reviewer_prompt(state, str(report), max_chars=settings.llm_max_input_chars)
    try:
        review_text = await provider.complete(
            [
                LLMMessage(role="system", content=REVIEWER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ]
        )
    except LLMProviderError as exc:
        return {
            "llm_review": LLMReview(
                passed=False,
                safe_to_return=False,
                issues=[exc.__class__.__name__],
                fallback_required=True,
            ).model_dump(),
            "llm_error": exc.__class__.__name__,
        }

    review = parse_review_json(review_text)
    return {"llm_review": review.model_dump()}


async def select_final_answer(state: AgentState) -> dict:
    review = state.get("llm_review") or {}
    if (
        state.get("llm_report")
        and review.get("passed") is True
        and review.get("safe_to_return") is True
        and review.get("fallback_required") is not True
    ):
        return {
            "final_answer": state["llm_report"],
            "llm_used": True,
            "final_answer_source": "llm",
            "fallback_reason": None,
        }
    fallback_reason = state.get("llm_error")
    if review.get("fallback_required") is True:
        fallback_reason = fallback_reason or "LLM_REVIEW_FAILED"
    return {
        "final_answer": state.get("deterministic_answer") or state.get("final_answer") or "",
        "llm_used": False,
        "final_answer_source": "deterministic",
        "fallback_reason": fallback_reason,
    }
