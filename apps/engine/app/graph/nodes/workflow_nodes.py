import json
import os
import re

import httpx
import structlog

from app.tools.mcp_client import get_formatted_tool_list
from app.tools.registry import execute_tool
from app.graph.state import AgentState
from app.llm.provider_factory import factory as llm_factory
from app.prompts.vcenter_admin import SYSTEM_PROMPT, build_user_prompt
from app.safety.redaction import redact_context
from app.formatters.fallback_formatter import format_fallback_answer

logger = structlog.get_logger()

# ── Intent classification ───────────────────────────────────────────────────


def _classify_intent(message: str) -> tuple[str, str | None]:
    """Classify user prompt into an intent. Returns (intent, extracted_entity)."""
    lower = message.lower().strip()

    # Extract entity name from patterns like "inspect X", "show X details", etc.
    entity = None
    for pattern in [r"get\s+details\s+for\s+(\S+)", r"inspect\s+(\S+)",
                    r"show\s+(\S+)\s+details?", r"what host is\s+(\S+)",
                    r"details?\s+(?:of|for|on)\s+(\S+)", r"info\s+(?:of|for|on)\s+(\S+)",
                    r"what\s+is\s+the\s+ip\s+of\s+(\S+)", r"datastore\s+of\s+(\S+)",
                    r"what\s+vms?\s+are\s+running\s+on\s+(\S+)"]:
        m = re.search(pattern, lower)
        if m:
            entity = m.group(1)
            break

    # Typo-tolerant risky action detection (before tool routing)
    risky_patterns = [
        r"\b(?:trun|tunr|turn|power|start|boot)\b.*\b(?:on|up)\b",
        r"\b(?:turn|power|shut)\b.*\b(?:off|down)\b",
        r"\b(?:reboot|restart|reset)\b",
        r"\b(?:delete|destroy|remove)\b.*\b(?:vm|snapshot|host)\b",
        r"\b(?:migrate|vmotion)\b",
        r"\bmaintenance\s+mode\b",
        r"\bsnapshot\s+(?:delete|revert|remove)\b",
        r"\bcreate\s+(?:vm|snapshot)\b",
        r"\brevert\b.*\bsnapshot\b",
    ]
    for pattern in risky_patterns:
        if re.search(pattern, lower):
            return ("risky_operation", entity)

    # ── Entity-based routing (must come before keyword routing) ─────────

    def _is_host_like(name: str) -> bool:
        lower_n = name.lower()
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", lower_n):
            return True
        if lower_n.startswith("esxi") or lower_n.startswith("esx-") or lower_n.startswith("esx."):
            return True
        host_keywords = ["host", "esxi", "esx-", "esx.", "hypervisor", "baremetal"]
        if any(k in lower_n for k in host_keywords):
            return True
        return False

    if entity:
        if _is_host_like(entity):
            return ("get_host_details", entity)
        return ("get_vm_details", entity)

    # Keyword-based routing (only when no entity was extracted)
    if any(w in lower for w in ["list tool", "show tool", "available tool", "what tool", "list down all the tool"]):
        return ("list_tools", None)

    if any(w in lower for w in ["environment", "overview", "summary of", "status of vcenter"]):
        return ("environment_overview", None)

    if any(w in lower for w in ["powered off", "not powered on", "power off vm", "which vms are off"]):
        return ("get_powered_off_vms", None)

    if any(w in lower for w in ["datastore health", "above 90", "critical datastore", "disk usage",
                                  "storage health", "datastore usage"]):
        return ("datastore_health", None)

    if any(w in lower for w in ["alarm", "active alarm", "triggered alarm", "alert"]):
        return ("active_alarms", None)

    if any(w in lower for w in ["recent event", "event log", "task", "show event"]):
        return ("recent_events", None)

    if any(w in lower for w in ["rke2", "kubernetes", "k8s", "cluster vm", "agentic"]):
        return ("rke2_vms", None)

    if any(w in lower for w in ["search inventory", "find in inventory", "search for"]):
        return ("search_inventory", None)

    if any(w in lower for w in ["datastore", "storage"]):
        return ("list_datastores", None)

    if any(w in lower for w in ["network", "port group"]):
        return ("list_networks", None)

    if any(w in lower for w in ["cluster"]):
        return ("list_clusters", None)

    if any(w in lower for w in ["host details", "esxi details", "show host", "host info", "host", "esxi"]):
        return ("list_hosts", None)

    if any(w in lower for w in ["vm", "virtual machine"]):
        return ("list_vms", None)

    # Fallback: environment overview
    return ("environment_overview", None)


def _intent_to_tools(intent: str) -> list[str]:
    """Map an intent to the primary tool(s) to execute."""
    mapping: dict[str, list[str]] = {
        "list_tools": ["list_available_tools"],
        "environment_overview": ["get_environment_overview"],
        "list_vms": ["list_vms"],
        "list_hosts": ["list_hosts"],
        "list_datastores": ["list_datastores"],
        "list_networks": ["list_networks"],
        "list_clusters": ["list_clusters"],
        "get_vm_details": ["get_vm_details"],
        "get_host_details": ["get_host_details"],
        "datastore_health": ["get_datastore_health"],
        "active_alarms": ["get_active_alarms"],
        "recent_events": ["get_recent_events"],
        "rke2_vms": ["get_rke2_vms"],
        "get_powered_off_vms": ["get_powered_off_vms"],
        "search_inventory": ["search_inventory_object"],
    }
    return mapping.get(intent, ["get_environment_overview"])


# ── Graph nodes ──────────────────────────────────────────────────────────────


async def load_session_node(state: AgentState) -> dict[str, object]:
    return {
        "turn": int(state.get("turn", 0)) + 1,
        "status": "thinking",
    }


async def classify_request_node(state: AgentState) -> dict[str, object]:
    message = state["user_message"]
    intent, entity = _classify_intent(message)
    tools = _intent_to_tools(intent)

    if intent == "risky_operation":
        return {
            "status": "blocked",
            "safety_verdict": {
                "blocked": True,
                "risk": "approval_required",
                "reason": "HIGH_RISK_ACTION",
                "message": (
                    "This is a high-risk vCenter action and is disabled in Phase 1.4. "
                    "Power operations, deletions, snapshots, migrations, and maintenance mode "
                    "changes require approval gates planned for a future phase. "
                    "I can inspect VMs and show their current state if you'd like."
                ),
            },
        }

    return {
        "intent": intent,
        "entity": entity,
        "selected_tools": tools,
        "status": "running_tool",
    }


async def safety_check_node(state: AgentState) -> dict[str, object]:
    # Safety is now handled in classify_request_node
    # This node validates and adds context-specific safety
    intent = state.get("intent", "")
    if intent == "risky_operation":
        return {"status": "blocked"}
    return {"status": state.get("status", "running_tool")}


async def select_tools_node(state: AgentState) -> dict[str, object]:
    return {"selected_tools": state.get("selected_tools", ["get_environment_overview"])}


async def execute_tools_node(state: AgentState) -> dict[str, object]:
    tools_to_run = state.get("selected_tools", ["get_environment_overview"])
    entity = state.get("entity")
    intent = state.get("intent", "")
    results: list[dict] = []

    for tool_name in tools_to_run:
        args = {}
        if tool_name in ("get_vm_details", "get_host_details") and entity:
            args["name"] = entity
        elif tool_name == "search_inventory_object" and entity:
            args["q"] = entity
        result = await execute_tool(tool_name, args)
        # Build summary field for downstream
        if result.get("ok"):
            data_count = len(result.get("items", [])) if "items" in result else (1 if result.get("data") else 0)
            result["summary"] = f"Found {data_count} result(s) for {tool_name}."
        else:
            result["summary"] = result.get("message", f"Tool {tool_name} failed.")
            result["status"] = "error"
        if result.get("cached"):
            result["status"] = "cache_hit"
        elif result.get("ok"):
            result["status"] = "success"
        else:
            result["status"] = "error"
        results.append(result)

    return {"tool_results": results, "status": "streaming"}


async def prepare_llm_context_node(state: AgentState) -> dict[str, object]:
    intent = state.get("intent", "")
    entity = state.get("entity")
    tool_results = state.get("tool_results", [])
    safety = state.get("safety_verdict", {"blocked": False, "risk": "read_only"})

    tool_trace = []
    for tr in tool_results:
        tool_trace.append({
            "tool": tr.get("tool", "unknown"),
            "status": tr.get("status", "unknown"),
            "summary": tr.get("summary", ""),
        })

    llm_context = {
        "user_message": state.get("user_message", ""),
        "intent": intent,
        "target_type": "host" if intent == "get_host_details" else ("vm" if intent == "get_vm_details" else None),
        "target_name": entity,
        "safety": safety,
        "tool_trace": tool_trace,
        "tool_results": tool_results,
        "page_context": state.get("page_context"),
        "provider": state.get("provider", ""),
        "model": state.get("model", ""),
    }

    redacted = redact_context(llm_context)
    logger.debug("llm_context_prepared", context=redacted, session_id=state.get("session_id", ""))

    return {"llm_context": llm_context}


async def generate_llm_answer_node(state: AgentState) -> dict[str, object]:
    intent = state.get("intent", "")
    entity = state.get("entity")
    tool_results = state.get("tool_results", [])
    llm_context = state.get("llm_context", {})

    blocked = state.get("status") == "blocked"
    safety_verdict = state.get("safety_verdict", {})

    if blocked:
        answer, next_step = format_fallback_answer(
            intent=intent, entity=entity, tool_results=tool_results,
            blocked=True, safety_message=safety_verdict.get("message"),
        )
        return {"final_answer": answer, "suggested_next": next_step, "status": "done", "answer_source": "blocked"}

    provider = llm_context.get("provider", state.get("provider", "")) or "gemini"
    model = llm_context.get("model", state.get("model", "")) or "gemini-2.5-flash"

    client = llm_factory.get_client(provider)
    llm_configured = client is not None

    if llm_configured:
        try:
            user_prompt = build_user_prompt(llm_context)
            answer = await client.generate(SYSTEM_PROMPT, user_prompt, model)

            if answer and len(answer) > 20:
                suggested = None
                if "suggested next step" in answer.lower():
                    suggested = None
                return {"final_answer": answer, "suggested_next": suggested, "status": "done", "answer_source": "llm"}

            logger.warning("llm_returned_empty", provider=provider)
        except Exception as exc:
            logger.warning("llm_generation_failed", provider=provider, error=str(exc)[:120])

    answer, next_step = format_fallback_answer(
        intent=intent, entity=entity, tool_results=tool_results,
    )
    return {"final_answer": answer, "suggested_next": next_step, "status": "done", "answer_source": "fallback"}


async def save_session_node(state: AgentState) -> dict[str, object]:
    return {}



