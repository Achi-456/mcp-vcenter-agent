from __future__ import annotations

import re
from typing import Any

from app.db.models import ChatMessage, ChatSession, ToolCall
from app.repositories.chat_repository import ChatRepository

ENTITY_KEYS = ("vm", "host", "datastore")
SENSITIVE_KEYS = ("password", "token", "secret", "api_key", "authorization", "cookie")


async def build_conversation_context(repo: ChatRepository, session: ChatSession) -> dict[str, Any]:
    messages = await repo.recent_messages(session.id, limit=10)
    latest_run = await repo.latest_run(session.id)
    tool_calls = await repo.latest_tool_summaries(session.id, limit=10)
    last_answer = next((item.content for item in reversed(messages) if item.role == "assistant"), "")
    return {
        "recent_messages": [_message_context(item) for item in messages],
        "last_entities": session.last_entities_json or infer_entities(messages, tool_calls),
        "last_intent": session.last_intent,
        "last_tool_results_summary": [_tool_context(item) for item in tool_calls],
        "last_answer_summary": _truncate(last_answer, 1200),
        "last_run_metadata": _redact(latest_run.output_json or {}) if latest_run else {},
    }


def infer_entities(messages: list[ChatMessage], tool_calls: list[ToolCall]) -> dict[str, str]:
    entities: dict[str, str] = {}
    for call in tool_calls:
        summary = " ".join(part for part in (call.input_summary, call.output_summary) if part)
        for key in ENTITY_KEYS:
            value = _extract_named(summary, key)
            if value:
                entities[key] = value
    for message in messages:
        metadata_entities = (message.metadata_json or {}).get("entities")
        if isinstance(metadata_entities, dict):
            for key in ENTITY_KEYS:
                value = metadata_entities.get(key)
                if isinstance(value, str) and value:
                    entities[key] = value
    return entities


def _message_context(message: ChatMessage) -> dict[str, Any]:
    return {
        "role": message.role,
        "content": _truncate(message.content, 1200),
        "created_at": message.created_at.isoformat(),
        "metadata": _redact(message.metadata_json or {}),
    }


def _tool_context(call: ToolCall) -> dict[str, Any]:
    return {
        "tool_name": call.tool_name,
        "status": call.status,
        "input_summary": _truncate(call.input_summary or "", 500),
        "output_summary": _truncate(call.output_summary or "", 800),
        "summary": _redact(call.summary_json or {}),
    }


def _extract_named(text: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}\s*[=:]\s*([^\s,;]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _truncate(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if any(secret in str(key).lower() for secret in SENSITIVE_KEYS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value[:20]]
    return value

