"""
Merges vCenter (registry) tools with govc and web search for the advanced agent.
"""
from __future__ import annotations

from typing import Any, Callable

from app.tools.registry import get_dynamic_tools, invoke_tool, reload_tools
from app.tools import integrations_govc as govc
from app.tools import integrations_search as search


def emit_session_report(
    objective: str,
    what_i_did: str,
    evidence: str,
    risks: str = "",
    open_questions: str = "",
    citations: str = "",
) -> dict[str, Any]:
    """
    Structured handoff report. Call once near the end of substantive tasks
    (same information as the markdown report template).
    """
    return {
        "objective": (objective or "").strip(),
        "what_i_did": (what_i_did or "").strip(),
        "evidence": (evidence or "").strip(),
        "risks": (risks or "").strip(),
        "open_questions": (open_questions or "").strip(),
        "citations": (citations or "").strip(),
        "emitted": True,
    }


EMIT_REPORT_TOOL = {
    "name": "emit_session_report",
    "description": (
        "Emit a structured session report (objective, actions, evidence, risks, open questions, citations). "
        "Use for multi-step or investigative tasks, in addition to or instead of the markdown report template."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "objective": {"type": "string"},
            "what_i_did": {"type": "string"},
            "evidence": {"type": "string"},
            "risks": {"type": "string", "description": "Risks and follow-ups (optional)."},
            "open_questions": {"type": "string", "description": "Open questions (optional)."},
            "citations": {
                "type": "string",
                "description": "Web/doc citations (optional; URLs and titles).",
            },
        },
        "required": ["objective", "what_i_did", "evidence"],
    },
}


GOVC_TOOL = {
    "name": "govc_command",
    "description": (
        "Run a restricted `govc` CLI command (VMware govmomi govc). "
        "Pass a single string `args` with everything after `govc`, e.g. "
        "'vm.info -json /dc/vm/Name' or 'find / -type m'. "
        "Destructive subcommands are blocked. Requires govc on PATH and GOVC_* (or VCENTER_*) env."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "args": {
                "type": "string",
                "description": "Argument string for govc (not including the word govc).",
            }
        },
        "required": ["args"],
    },
}

WEB_TOOL = {
    "name": "web_search",
    "description": (
        "Search the public web (Tavily) for documentation, KB articles, and best practices. "
        "Not authoritative for your vCenter inventory; use vCenter tools for that. "
        "Set TAVILY_API_KEY on the server to enable."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Number of results (1–10).",
            },
        },
        "required": ["query"],
    },
}


def build_combined_tools() -> tuple[list[dict], dict[str, Callable[..., Any]]]:
    """Return Anthropic tool list + name -> callable for both vcenter and add-ons."""
    v_tools, v_dispatch = get_dynamic_tools()
    extra: list[dict] = [GOVC_TOOL, WEB_TOOL, EMIT_REPORT_TOOL]
    merged = extra + v_tools
    merged.sort(key=lambda t: t["name"])

    dispatch: dict[str, Callable[..., Any]] = dict(v_dispatch)
    dispatch["govc_command"] = govc.govc_command
    dispatch["web_search"] = search.web_search
    dispatch["emit_session_report"] = emit_session_report
    return merged, dispatch


def execute_combined(
    name: str, arguments: dict | None, dispatch: dict[str, Callable[..., Any]] | None = None
) -> Any:
    """
    Run one tool. Uses invoke_tool for vcenter-only names; add-ons are direct in dispatch.
    """
    if arguments is None:
        arguments = {}
    if dispatch is None:
        _, dispatch = build_combined_tools()
    if name not in dispatch:
        return {"error": f"Unknown tool: {name}"}
    if name in ("govc_command", "web_search", "emit_session_report"):
        fn = dispatch[name]
        return fn(**arguments)
    return invoke_tool(name, arguments, dispatch)


def reload_all_tools() -> None:
    """Reload vcenter module; integration modules do not need reload."""
    reload_tools()
