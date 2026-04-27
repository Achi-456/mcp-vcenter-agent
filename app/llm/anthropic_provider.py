"""Anthropic Claude provider."""
from __future__ import annotations

import os
from typing import Iterator

import anthropic

from app.llm.base import StepResult, NormalizedMessage, ToolUsePart
from app.llm.retry import with_retry
from app.llm.schema_sanitize import to_anthropic_tools


DEFAULT_MODEL = "claude-sonnet-4-20250514"

CURATED_MODELS = [
    {"id": "claude-sonnet-4-20250514", "display": "Claude Sonnet 4"},
    {"id": "claude-3-7-sonnet-latest", "display": "Claude 3.7 Sonnet"},
    {"id": "claude-3-5-sonnet-latest", "display": "Claude 3.5 Sonnet"},
    {"id": "claude-3-5-haiku-latest", "display": "Claude 3.5 Haiku"},
    {"id": "claude-3-opus-latest", "display": "Claude 3 Opus"},
]


class AnthropicProvider:
    name = "anthropic"
    env_key = "ANTHROPIC_API_KEY"
    default_model = DEFAULT_MODEL

    def __init__(self) -> None:
        self._client: anthropic.Anthropic | None = None

    def is_configured(self) -> bool:
        return bool(os.environ.get(self.env_key, "").strip())

    def _client_or_raise(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=os.environ[self.env_key])
        return self._client

    def list_models(self) -> list[dict]:
        if not self.is_configured():
            return CURATED_MODELS
        try:
            client = self._client_or_raise()
            resp = client.models.list()
            result = []
            for m in getattr(resp, "data", []) or []:
                mid = getattr(m, "id", None)
                if not mid:
                    continue
                result.append({"id": mid, "display": getattr(m, "display_name", None) or mid})
            # Prepend curated defaults (dedup) if API returned empty
            if not result:
                return CURATED_MODELS
            known = {x["id"] for x in result}
            for c in CURATED_MODELS:
                if c["id"] not in known:
                    result.append(c)
            return result
        except Exception:
            return CURATED_MODELS

    # ── Message translation ────────────────────────────

    @staticmethod
    def _to_native_messages(messages: list[NormalizedMessage]) -> list[dict]:
        """Normalized → Anthropic. Parts map 1:1 (tool_use, tool_result supported natively)."""
        native: list[dict] = []
        for m in messages:
            c = m.get("content")
            if isinstance(c, str):
                native.append({"role": m["role"], "content": c})
                continue
            # list of parts
            blocks = []
            for p in c or []:
                pt = p.get("type")
                if pt == "text":
                    blocks.append({"type": "text", "text": p.get("text", "")})
                elif pt == "tool_use":
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": p["id"],
                            "name": p["name"],
                            "input": p.get("input") or {},
                        }
                    )
                elif pt == "tool_result":
                    blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": p["tool_use_id"],
                            "content": p.get("content", ""),
                        }
                    )
            # Anthropic requires user-role for tool_result blocks
            role = m.get("role", "assistant")
            if any(b.get("type") == "tool_result" for b in blocks):
                role = "user"
            native.append({"role": role, "content": blocks})
        return native

    # ── Streaming step ────────────────────────────────

    @staticmethod
    def _collect_stream(
        client: anthropic.Anthropic,
        *,
        model: str,
        max_tokens: int,
        system: str,
        tools: list[dict],
        messages: list[dict],
    ) -> tuple[list[dict], StepResult]:
        """Run one full stream and return (buffered_events, step).

        Raises anthropic.RateLimitError on 429 so with_retry can catch it.
        Raises anthropic.APIError for other non-retryable API failures.
        """
        events: list[dict] = []
        step = StepResult()

        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        ) as stream:
            for event in stream:
                et = getattr(event, "type", None)
                if et == "content_block_delta":
                    delta = event.delta
                    if hasattr(delta, "text") and delta.text:
                        step.text += delta.text
                        events.append({"type": "text", "content": delta.text})
            final_msg = stream.get_final_message()

        parts: list[dict] = []
        for b in final_msg.content:
            if b.type == "text":
                parts.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                tu: ToolUsePart = {
                    "type": "tool_use",
                    "id": b.id,
                    "name": b.name,
                    "input": b.input or {},
                }
                parts.append(tu)
                step.tool_uses.append(tu)

        step.assistant_message = {"role": "assistant", "content": parts}
        step.stop_reason = "tool_use" if step.tool_uses else (final_msg.stop_reason or "end_turn")

        usage = getattr(final_msg, "usage", None)
        if usage is not None:
            step.input_tokens = getattr(usage, "input_tokens", 0) or 0
            step.output_tokens = getattr(usage, "output_tokens", 0) or 0
            events.append({
                "type": "usage",
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
            })

        return events, step

    def stream_step(
        self,
        *,
        system: str,
        messages: list[NormalizedMessage],
        tools: list[dict],
        model: str,
        max_tokens: int,
    ) -> Iterator[dict]:
        client = self._client_or_raise()
        nt = to_anthropic_tools(tools)
        nm = self._to_native_messages(messages)

        step = StepResult()
        try:
            events, step = with_retry(
                lambda: self._collect_stream(
                    client,
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    tools=nt,
                    messages=nm,
                ),
                retryable_exc=anthropic.RateLimitError,
            )
            yield from events
        except RuntimeError:
            # Retry exhaustion — propagate so FailoverProvider can catch it.
            raise
        except anthropic.APIError as e:
            yield {"type": "error", "error": f"Anthropic API: {type(e).__name__}: {getattr(e, 'message', str(e))}"}
            step.stop_reason = "error"

        yield {"type": "step_result", "result": step}
