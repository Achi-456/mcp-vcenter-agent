"""Google Gemini provider via google-genai SDK."""
from __future__ import annotations

import json
import os
from typing import Iterator

try:
    from google import genai  # type: ignore
    from google.genai import types as gtypes  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    genai = None  # type: ignore
    gtypes = None  # type: ignore

try:
    from google.api_core.exceptions import ResourceExhausted as _GeminiRateLimitError  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    _GeminiRateLimitError = type(None)  # type: ignore  # sentinel — never matches

from app.llm.base import StepResult, NormalizedMessage, ToolUsePart
from app.llm.retry import with_retry
from app.llm.schema_sanitize import to_gemini_tools


GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"

GEMINI_CURATED = [
    {"id": "gemini-2.5-pro", "display": "Gemini 2.5 Pro"},
    {"id": "gemini-2.5-flash", "display": "Gemini 2.5 Flash"},
    {"id": "gemini-2.5-flash-lite", "display": "Gemini 2.5 Flash Lite"},
    {"id": "gemini-2.0-flash", "display": "Gemini 2.0 Flash"},
    {"id": "gemini-1.5-pro", "display": "Gemini 1.5 Pro"},
    {"id": "gemini-1.5-flash", "display": "Gemini 1.5 Flash"},
]


class GeminiProvider:
    name = "gemini"
    env_key = "GOOGLE_API_KEY"
    default_model = GEMINI_DEFAULT_MODEL

    def __init__(self) -> None:
        self._client = None

    def is_configured(self) -> bool:
        return bool(os.environ.get(self.env_key, "").strip()) and genai is not None

    def _client_or_raise(self):
        if self._client is None:
            if genai is None:
                raise RuntimeError("google-genai SDK not installed")
            self._client = genai.Client(api_key=os.environ[self.env_key])
        return self._client

    def list_models(self) -> list[dict]:
        if not self.is_configured():
            return GEMINI_CURATED
        try:
            client = self._client_or_raise()
            models = client.models.list()
            out = []
            for m in models:
                mid = getattr(m, "name", "") or ""
                if mid.startswith("models/"):
                    mid = mid[len("models/"):]
                if not mid:
                    continue
                if "gemini" not in mid.lower():
                    continue
                methods = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or []
                if methods and "generateContent" not in methods:
                    continue
                out.append({"id": mid, "display": mid})
            # Put curated at top if present
            curated_ids = [c["id"] for c in GEMINI_CURATED]
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
            return ordered or GEMINI_CURATED
        except Exception:
            return GEMINI_CURATED

    @staticmethod
    def _to_native_contents(messages: list[NormalizedMessage]) -> list[dict]:
        """Gemini uses 'contents' = [{role, parts:[{text|function_call|function_response}]}]."""
        contents: list[dict] = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            c = m.get("content")
            parts_out: list[dict] = []
            if isinstance(c, str):
                parts_out.append({"text": c})
            else:
                for p in c or []:
                    pt = p.get("type")
                    if pt == "text":
                        if p.get("text"):
                            parts_out.append({"text": p["text"]})
                    elif pt == "tool_use":
                        parts_out.append(
                            {
                                "function_call": {
                                    "name": p["name"],
                                    "args": p.get("input") or {},
                                }
                            }
                        )
                    elif pt == "tool_result":
                        # Try to parse back to object; else wrap.
                        raw = p.get("content", "")
                        try:
                            resp_obj = json.loads(raw) if isinstance(raw, str) else raw
                        except Exception:
                            resp_obj = {"output": raw}
                        if not isinstance(resp_obj, dict):
                            resp_obj = {"output": resp_obj}
                        # function_response belongs to 'user' role in Gemini
                        role = "user"
                        parts_out.append(
                            {
                                "function_response": {
                                    "name": p.get("tool_use_id", "tool"),
                                    "response": resp_obj,
                                }
                            }
                        )
            if parts_out:
                contents.append({"role": role, "parts": parts_out})
        return contents

    @staticmethod
    def _collect_stream(
        client,
        *,
        model: str,
        contents: list[dict],
        config: dict,
    ) -> tuple[list[dict], StepResult]:
        """Run one full Gemini stream and return (buffered_events, step).

        Raises _GeminiRateLimitError (ResourceExhausted / 429) so with_retry can catch it.
        All other exceptions propagate immediately.
        """
        events: list[dict] = []
        step = StepResult()
        text_acc = ""
        tool_uses: list[ToolUsePart] = []
        last_usage = None
        idx_counter = 0

        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )
        for chunk in stream:
            um = getattr(chunk, "usage_metadata", None)
            if um is not None:
                last_usage = um
            cands = getattr(chunk, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    ptxt = getattr(part, "text", None)
                    if ptxt:
                        events.append({"type": "text", "content": ptxt})
                        text_acc += ptxt
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        name = getattr(fc, "name", None)
                        args = getattr(fc, "args", None) or {}
                        if name:
                            tu: ToolUsePart = {
                                "type": "tool_use",
                                "id": f"gemini_tu_{idx_counter}",
                                "name": name,
                                "input": dict(args) if hasattr(args, "items") else (args if isinstance(args, dict) else {}),
                            }
                            idx_counter += 1
                            tool_uses.append(tu)

        parts_out: list[dict] = []
        if text_acc:
            parts_out.append({"type": "text", "text": text_acc})
        parts_out.extend(tool_uses)

        step.text = text_acc
        step.tool_uses = tool_uses
        step.assistant_message = {"role": "assistant", "content": parts_out}
        step.stop_reason = "tool_use" if tool_uses else "end_turn"

        if last_usage is not None:
            step.input_tokens = getattr(last_usage, "prompt_token_count", 0) or 0
            step.output_tokens = getattr(last_usage, "candidates_token_count", 0) or 0
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
        step = StepResult()
        try:
            client = self._client_or_raise()
            contents = self._to_native_contents(messages)
            tool_decls = to_gemini_tools(tools)

            config: dict = {
                "system_instruction": system,
                "max_output_tokens": max_tokens,
            }
            if tool_decls:
                config["tools"] = [{"function_declarations": tool_decls}]
                config["tool_config"] = {"function_calling_config": {"mode": "AUTO"}}

            events, step = with_retry(
                lambda: self._collect_stream(
                    client,
                    model=model,
                    contents=contents,
                    config=config,
                ),
                retryable_exc=_GeminiRateLimitError,
            )
            yield from events
        except RuntimeError:
            # Retry exhaustion — propagate so FailoverProvider can catch it.
            raise
        except Exception as e:
            yield {"type": "error", "error": f"{self.name} API: {type(e).__name__}: {e}"}
            step.stop_reason = "error"

        yield {"type": "step_result", "result": step}
