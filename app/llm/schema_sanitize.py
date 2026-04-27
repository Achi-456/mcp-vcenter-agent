"""Per-provider JSON Schema sanitization for tool parameters.

pyVmomi tool schemas come from app.tools.registry.get_dynamic_tools() with:
  {name, description, input_schema: {type, properties, required?}}
Each provider has different subset of JSON Schema it accepts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


# ─────────────────────────────────────────────
# OpenAI / Grok (OpenAI-compatible)
# ─────────────────────────────────────────────

def to_openai_tools(tools: list[dict]) -> list[dict]:
    """OpenAI chat.completions tools: [{type:'function', function:{name, description, parameters}}]."""
    out: list[dict] = []
    for t in tools:
        params = deepcopy(t.get("input_schema") or {"type": "object", "properties": {}})
        # OpenAI rejects missing "type" at top level; ensure object
        params.setdefault("type", "object")
        params.setdefault("properties", {})
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": (t.get("description") or "")[:1024],
                    "parameters": params,
                },
            }
        )
    return out


# ─────────────────────────────────────────────
# Google Gemini
# ─────────────────────────────────────────────

_GEMINI_STRIP_KEYS = {"default", "additionalProperties", "$schema", "examples", "title", "anyOf", "oneOf", "allOf"}
_GEMINI_ALLOWED_TYPES = {"object", "array", "string", "integer", "number", "boolean"}


def _gemini_clean_schema(node: Any) -> Any:
    """Strip / coerce keys that Gemini function declarations reject."""
    if not isinstance(node, dict):
        return node
    cleaned: dict[str, Any] = {}
    for k, v in node.items():
        if k in _GEMINI_STRIP_KEYS:
            continue
        if k == "type" and isinstance(v, str) and v not in _GEMINI_ALLOWED_TYPES:
            cleaned["type"] = "string"
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned[k] = {p: _gemini_clean_schema(pv) for p, pv in v.items()}
        elif k == "items":
            cleaned[k] = _gemini_clean_schema(v)
        elif isinstance(v, dict):
            cleaned[k] = _gemini_clean_schema(v)
        else:
            cleaned[k] = v
    return cleaned


def to_gemini_tools(tools: list[dict]) -> list[dict]:
    """Return a list of Gemini FunctionDeclaration-shaped dicts (the SDK accepts plain dicts)."""
    out = []
    for t in tools:
        params = _gemini_clean_schema(t.get("input_schema") or {"type": "object", "properties": {}})
        params.setdefault("type", "object")
        params.setdefault("properties", {})
        out.append(
            {
                "name": t["name"],
                "description": (t.get("description") or "")[:1024],
                "parameters": params,
            }
        )
    return out


# ─────────────────────────────────────────────
# Anthropic
# ─────────────────────────────────────────────

def to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """Anthropic expects {name, description, input_schema}. Pass through."""
    return [
        {
            "name": t["name"],
            "description": (t.get("description") or "")[:1024],
            "input_schema": t.get("input_schema") or {"type": "object", "properties": {}},
        }
        for t in tools
    ]
