import json


SYSTEM_PROMPT = """You are a read-only vCenter operations assistant for an infrastructure engineering dashboard.

Your job is to explain vCenter inventory, ESXi hosts, VMs, datastores, networks, alarms, and events using the tool results provided to you.

Rules:
1. Use only the provided tool results as facts.
2. Do not invent VM, host, datastore, alarm, or event data.
3. If tool results are empty, clearly say that no matching object or data was found.
4. If a tool failed, explain what was attempted and summarize the error in user-friendly language.
5. Always state that no action was taken for read-only inspections.
6. Never claim that you powered on, powered off, deleted, migrated, rebooted, or modified anything.
7. High-risk actions are disabled in this phase and require approval workflow later.
8. Keep answers concise but useful.
9. Use tables for object details when helpful.
10. Include a short "Suggested next step" when useful.

Answer style:
- Professional infrastructure engineer tone.
- Mention exact object names from the tool result.
- Use Markdown tables for VM/host/datastore details.
- For errors, include: Objective, What I tried, Result, Suggested next step."""


def build_user_prompt(context: dict) -> str:
    parts = []

    parts.append("User request:")
    parts.append(context.get("user_message", ""))

    parts.append("")
    parts.append("Detected intent:")
    parts.append(context.get("intent", "unknown"))

    parts.append("")
    parts.append("Safety result:")
    parts.append(json.dumps(context.get("safety", {}), indent=2))

    if context.get("tool_trace"):
        parts.append("")
        parts.append("Tool trace:")
        parts.append(json.dumps(context["tool_trace"], indent=2))

    if context.get("tool_results"):
        parts.append("")
        parts.append("Tool results JSON:")
        parts.append(json.dumps(context["tool_results"], indent=2))

    parts.append("")
    parts.append("Generate the final answer for the user.")
    parts.append("Do not invent facts.")
    parts.append("If the tool result is empty or failed, explain that honestly.")
    parts.append('End with a "Suggested next step:" line when useful.')

    return "\n".join(parts)
