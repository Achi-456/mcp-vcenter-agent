from __future__ import annotations

from typing import Any

from app.graph.state import AgentState

FOLLOWUP_TERMS = (
    " it ",
    " this ",
    " that ",
    " that vm",
    " this vm",
    " that host",
    " this host",
    " that datastore",
    " this datastore",
    " previous one",
    " which one",
)


async def context_resolver_node(state: AgentState) -> dict[str, Any]:
    message = str(state.get("user_message") or "")
    lowered = f" {message.lower().strip()} "
    context = state.get("conversation_context") or {}
    if not _is_followup(lowered):
        return {"original_user_message": message, "context_resolution": {"resolved": False, "reason": "not_followup"}}

    entities = _last_entities(context)
    datastore_context = _has_datastore_context(context)

    if "which one" in lowered or "previous one" in lowered or "datastore" in lowered:
        datastore = entities.get("datastore")
        if datastore and "datastore" in lowered:
            return _resolved(message, f"show datastore summary for datastore={datastore}", "datastore", datastore)
        if datastore_context:
            return _resolved(message, "show datastore summary", "datastore", None)

    if ("host" in lowered or "compare" in lowered or "vm" in lowered or " it " in lowered or " this " in lowered or " that " in lowered) and entities.get("vm"):
        vm = entities["vm"]
        if "compare" in lowered and "govc" in lowered:
            return _resolved(message, f"compare pyVmomi and govc for vm={vm}", "vm", vm)
        return _resolved(message, f"inspect vm={vm}", "vm", vm)

    if ("alarm" in lowered or "event" in lowered or "host" in lowered or " it " in lowered) and entities.get("host"):
        host = entities["host"]
        return _resolved(message, f"check host host={host}", "host", host)

    if entities.get("datastore"):
        datastore = entities["datastore"]
        return _resolved(message, f"show datastore summary for datastore={datastore}", "datastore", datastore)

    return {
        "original_user_message": message,
        "task_type": "missing_input",
        "object_type": None,
        "tool_name": None,
        "tool_endpoint": None,
        "tool_input": {},
        "tool_calls": [],
        "context_resolution": {"resolved": False, "reason": "missing_context"},
    }


def _is_followup(lowered: str) -> bool:
    return any(term in lowered for term in FOLLOWUP_TERMS) or lowered.strip() in {
        "what host is it on?",
        "what host is it on",
        "compare it with govc",
        "which one is most critical?",
        "which one is most critical",
    }


def _last_entities(context: dict[str, Any]) -> dict[str, str]:
    raw = context.get("last_entities")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key in ("vm", "host", "datastore"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()
    return result


def _has_datastore_context(context: dict[str, Any]) -> bool:
    if "datastore" in str(context.get("last_intent") or "").lower():
        return True
    for item in context.get("last_tool_results_summary") or []:
        if isinstance(item, dict) and "datastore" in str(item.get("tool_name") or "").lower():
            return True
    return False


def _resolved(original: str, rewritten: str, object_type: str, entity: str | None) -> dict[str, Any]:
    return {
        "original_user_message": original,
        "user_message": rewritten,
        "context_resolution": {
            "resolved": True,
            "object_type": object_type,
            "entity": entity,
            "rewritten_message": rewritten,
        },
    }
