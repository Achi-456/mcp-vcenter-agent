"""OpenAI provider (also used as a base for Grok via base_url override)."""
from __future__ import annotations

import json
import logging
import os
from typing import Iterator, Optional

log = logging.getLogger(__name__)

try:
    from openai import OpenAI, RateLimitError as _OpenAIRateLimitError  # type: ignore
except Exception:  # pragma: no cover - openai optional at runtime
    OpenAI = None  # type: ignore
    _OpenAIRateLimitError = type(None)  # type: ignore  # sentinel — never matches

from app.llm.base import StepResult, NormalizedMessage, ToolUsePart
from app.llm.retry import with_retry
from app.llm.schema_sanitize import to_openai_tools


OPENAI_DEFAULT_MODEL = "gpt-4o"

OPENAI_CURATED = [
    {"id": "gpt-4o", "display": "GPT-4o"},
    {"id": "gpt-4o-mini", "display": "GPT-4o mini"},
    {"id": "gpt-4.1", "display": "GPT-4.1"},
    {"id": "gpt-4.1-mini", "display": "GPT-4.1 mini"},
    {"id": "o4-mini", "display": "o4-mini"},
]


class OpenAIProvider:
    name = "openai"
    env_key = "OPENAI_API_KEY"
    default_model = OPENAI_DEFAULT_MODEL
    base_url: Optional[str] = None
    # Some OpenAI-compatible APIs error on stream_options (e.g. Moonshot Kimi).
    stream_include_usage: bool = True

    def __init__(self) -> None:
        self._client = None  # type: ignore[assignment]

    def is_configured(self) -> bool:
        return bool(os.environ.get(self.env_key, "").strip()) and OpenAI is not None

    def _client_or_raise(self):
        if self._client is None:
            if OpenAI is None:
                raise RuntimeError("openai SDK not installed")
            kwargs = {"api_key": os.environ[self.env_key]}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)  # type: ignore[call-arg]
        return self._client

    def list_models(self) -> list[dict]:
        curated = self._curated_models()
        if not self.is_configured():
            return curated
        try:
            client = self._client_or_raise()
            models = client.models.list()
            data = getattr(models, "data", []) or []
            ids = [getattr(m, "id", None) for m in data]
            ids = [i for i in ids if i]
            # Filter to reasonable chat-capable ids for UX
            filt = [i for i in ids if self._is_chat_model(i)]
            if not filt:
                filt = ids
            out = [{"id": i, "display": i} for i in sorted(set(filt))]
            # Put curated at top if present
            curated_ids = [c["id"] for c in curated]
            seen = set()
            ordered: list[dict] = []
            for cid in curated_ids:
                hit = next((m for m in out if m["id"] == cid), None)
                if hit:
                    ordered.append(hit)
                    seen.add(cid)
            for m in out:
                if m["id"] not in seen:
                    ordered.append(m)
            return ordered or curated
        except Exception:
            return curated

    def _curated_models(self) -> list[dict]:
        return OPENAI_CURATED

    @staticmethod
    def _is_chat_model(mid: str) -> bool:
        low = mid.lower()
        if any(k in low for k in ("gpt-", "o1", "o3", "o4", "chatgpt")):
            return True
        return False

    # ── Message translation ────────────────────────────

    @staticmethod
    def _to_native_messages(
        messages: list[NormalizedMessage], system: str
    ) -> list[dict]:
        native: list[dict] = []
        if system:
            native.append({"role": "system", "content": system})
        for m in messages:
            role = m.get("role")
            c = m.get("content")
            if isinstance(c, str):
                native.append({"role": role, "content": c})
                continue
            if role == "assistant":
                text_parts = []
                tool_calls = []
                for p in c or []:
                    pt = p.get("type")
                    if pt == "text":
                        text_parts.append(p.get("text", ""))
                    elif pt == "tool_use":
                        tool_calls.append(
                            {
                                "id": p["id"],
                                "type": "function",
                                "function": {
                                    "name": p["name"],
                                    "arguments": json.dumps(p.get("input") or {}),
                                },
                            }
                        )
                msg: dict = {"role": "assistant"}
                if text_parts:
                    msg["content"] = "".join(text_parts)
                else:
                    msg["content"] = None
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                native.append(msg)
            else:  # user turn; may carry tool_result parts
                plain = []
                for p in c or []:
                    if p.get("type") == "tool_result":
                        native.append(
                            {
                                "role": "tool",
                                "tool_call_id": p["tool_use_id"],
                                "content": p.get("content", ""),
                            }
                        )
                    elif p.get("type") == "text":
                        plain.append(p.get("text", ""))
                if plain:
                    native.append({"role": "user", "content": "".join(plain)})
        return native

    def _collect_stream(
        self,
        client,
        *,
        model: str,
        messages: list[dict],
        tools: list[dict] | None,
        max_tokens: int,
        stream_include_usage: bool,
        provider_name: str,
    ) -> tuple[list[dict], StepResult]:
        """Run one full streaming completion and return (buffered_events, step).

        Raises _OpenAIRateLimitError on 429 so with_retry can catch and retry it.
        All other exceptions propagate immediately.
        """
        events: list[dict] = []
        step = StepResult()
        text_acc = ""
        tc_acc: dict[int, dict] = {}

        create_kwargs: dict = {
            "model": model,
            "messages": messages,
            "tools": tools if tools else None,
            "tool_choice": "auto" if tools else None,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if stream_include_usage:
            create_kwargs["stream_options"] = {"include_usage": True}

        stream = client.chat.completions.create(**create_kwargs)
        finish_reason = None
        last_usage = None

        for chunk in stream:
            choice = (chunk.choices or [None])[0]
            last_usage = getattr(chunk, "usage", None) or last_usage
            if not choice:
                continue
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            if getattr(delta, "content", None):
                events.append({"type": "text", "content": delta.content})
                text_acc += delta.content
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index if hasattr(tc, "index") else 0
                    entry = tc_acc.setdefault(idx, {"id": None, "name": None, "args": ""})
                    if getattr(tc, "id", None):
                        entry["id"] = tc.id
                    fn = getattr(tc, "function", None)
                    if fn is not None:
                        if getattr(fn, "name", None):
                            entry["name"] = fn.name
                        if getattr(fn, "arguments", None):
                            entry["args"] += fn.arguments
            fr = getattr(choice, "finish_reason", None)
            if fr is not None:
                finish_reason = fr

        tool_uses: list[ToolUsePart] = []
        parts: list[dict] = []
        if text_acc:
            parts.append({"type": "text", "text": text_acc})
        for idx in sorted(tc_acc.keys()):
            entry = tc_acc[idx]
            if not entry.get("name"):
                continue
            try:
                inp = json.loads(entry["args"] or "{}")
            except Exception:
                inp = {}
            tu: ToolUsePart = {
                "type": "tool_use",
                "id": entry.get("id") or f"tu_{idx}",
                "name": entry["name"],
                "input": inp,
            }
            parts.append(tu)
            tool_uses.append(tu)

        step.text = text_acc
        step.tool_uses = tool_uses
        step.assistant_message = {"role": "assistant", "content": parts}
        step.stop_reason = "tool_use" if tool_uses else (finish_reason or "end_turn")

        if last_usage is not None:
            step.input_tokens = getattr(last_usage, "prompt_tokens", 0) or 0
            step.output_tokens = getattr(last_usage, "completion_tokens", 0) or 0
            log.info(
                "%s USAGE: model=%s input=%s output=%s finish=%s tool_calls=%s",
                provider_name.upper(),
                model,
                step.input_tokens,
                step.output_tokens,
                finish_reason,
                len(tool_uses),
            )
            events.append({
                "type": "usage",
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
            })
        else:
            log.info(
                "%s USAGE: model=%s (no usage data) finish=%s tool_calls=%s",
                provider_name.upper(),
                model,
                finish_reason,
                len(tool_uses),
            )

        if not text_acc and not tool_uses and finish_reason != "error":
            log.warning(
                "%s returned EMPTY response (no text, no tool calls). "
                "Likely context window exhaustion. model=%s finish=%s input_tokens=%s",
                provider_name.upper(),
                model,
                finish_reason,
                getattr(last_usage, "prompt_tokens", "unknown") if last_usage else "unknown",
            )
            events.append({
                "type": "error",
                "error": (
                    f"{provider_name} returned an empty response — the model's context window "
                    f"is likely exhausted. Try a larger context model (e.g. moonshot-v1-32k "
                    f"or moonshot-v1-128k), reduce AGENT_MAX_TURNS, or disable "
                    f"AGENT_PLANNER / AGENT_MINITASK_LLM to save tokens."
                ),
            })
            step.stop_reason = "context_exhausted"

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
        nt = to_openai_tools(tools)
        nm = self._to_native_messages(messages, system)

        step = StepResult()
        try:
            events, step = with_retry(
                lambda: self._collect_stream(
                    client,
                    model=model,
                    messages=nm,
                    tools=nt,
                    max_tokens=max_tokens,
                    stream_include_usage=self.stream_include_usage,
                    provider_name=self.name,
                ),
                retryable_exc=_OpenAIRateLimitError,
            )
            yield from events
        except RuntimeError:
            # Retry exhaustion — propagate so FailoverProvider can catch it.
            raise
        except Exception as e:
            raw = str(e)
            if "401" in raw or "authentication" in raw.lower() or "unauthorized" in raw.lower():
                hint = f"{self.name.upper()} API key rejected (401 Unauthorized). Check your API key in ⚙ LLM keys."
            elif "429" in raw or "balance" in raw.lower() or "suspended" in raw.lower() or "quota" in raw.lower():
                hint = (
                    f"{self.name.upper()} API quota/balance error (429). "
                    "Your account may be out of credits — recharge at the provider dashboard."
                )
            elif "connection" in raw.lower() or "timeout" in raw.lower() or "network" in raw.lower():
                hint = f"{self.name.upper()} network error — check base URL and internet connectivity. ({type(e).__name__}: {raw[:120]})"
            else:
                hint = f"{self.name.upper()} API error: {type(e).__name__}: {raw[:200]}"
            yield {"type": "error", "error": hint}
            step.stop_reason = "error"

        yield {"type": "step_result", "result": step}


class GrokProvider(OpenAIProvider):
    """xAI Grok — OpenAI-compatible chat completions at /v1."""
    name = "grok"
    env_key = "XAI_API_KEY"
    default_model = "grok-2-latest"
    base_url = "https://api.x.ai/v1"

    def _curated_models(self) -> list[dict]:
        return [
            {"id": "grok-2-latest", "display": "Grok 2"},
            {"id": "grok-2-mini", "display": "Grok 2 mini"},
            {"id": "grok-beta", "display": "Grok beta"},
        ]

    @staticmethod
    def _is_chat_model(mid: str) -> bool:
        return "grok" in (mid or "").lower()


class KimiProvider(OpenAIProvider):
    """Moonshot AI Kimi — OpenAI-compatible API (Kimi K2 and related models)."""

    name = "kimi"
    env_key = "MOONSHOT_API_KEY"
    default_model = "moonshot-v1-32k"
    base_url = "https://api.moonshot.cn/v1"
    stream_include_usage = False

    def __init__(self) -> None:
        super().__init__()
        b = os.environ.get("MOONSHOT_BASE_URL", "").strip()
        if b:
            self.base_url = b
        m = os.environ.get("MOONSHOT_MODEL", "").strip()
        if m:
            self.default_model = m

    def _curated_models(self) -> list[dict]:
        return [
            {"id": "moonshot-v1-8k", "display": "Moonshot v1 8k (fast/free)"},
            {"id": "moonshot-v1-32k", "display": "Moonshot v1 32k"},
            {"id": "moonshot-v1-128k", "display": "Moonshot v1 128k"},
            {"id": "kimi-k2-0905", "display": "Kimi K2 (0905, large)"},
            {"id": "kimi-k2.5", "display": "Kimi K2.5"},
            {"id": "kimi-k2.6", "display": "Kimi K2.6"},
        ]

    @staticmethod
    def _is_chat_model(mid: str) -> bool:
        low = (mid or "").lower()
        return any(
            k in low for k in ("kimi-", "moonshot-", "kimi_", "moonshot_")
        )
