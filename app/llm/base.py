"""Canonical types + provider protocol for multi-LLM agent engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol, Literal, TypedDict


# ─────────────────────────────────────────────
# Canonical message schema (provider-agnostic)
# ─────────────────────────────────────────────

class TextPart(TypedDict):
    type: Literal["text"]
    text: str


class ToolUsePart(TypedDict):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict


class ToolResultPart(TypedDict):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str  # JSON-encoded string


Part = TextPart | ToolUsePart | ToolResultPart


class NormalizedMessage(TypedDict, total=False):
    role: Literal["user", "assistant"]
    content: str | list[Part]


# ─────────────────────────────────────────────
# Provider step result
# ─────────────────────────────────────────────

@dataclass
class StepResult:
    """Result of one LLM turn (streamed)."""
    assistant_message: NormalizedMessage = field(default_factory=lambda: {"role": "assistant", "content": []})
    stop_reason: str = "end_turn"  # "end_turn" | "tool_use" | other provider strings
    text: str = ""
    tool_uses: list[ToolUsePart] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


# ─────────────────────────────────────────────
# Provider protocol
# ─────────────────────────────────────────────

class LLMProvider(Protocol):
    name: str
    env_key: str
    default_model: str

    def is_configured(self) -> bool: ...

    def list_models(self) -> list[dict]:
        """Return [{id, display, context_window?}, ...]."""
        ...

    def stream_step(
        self,
        *,
        system: str,
        messages: list[NormalizedMessage],
        tools: list[dict],
        model: str,
        max_tokens: int,
    ) -> Iterator[dict]:
        """Yield dashboard-facing event dicts. Final yielded dict must be a 'step_result' with StepResult."""
        ...
