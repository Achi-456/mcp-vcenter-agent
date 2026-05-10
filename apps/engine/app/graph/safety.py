from app.graph.state import AgentState


BLOCKED_RISK = {"low_risk", "approval_required", "destructive"}


async def safety_agent_node(state: AgentState) -> dict:
    risk_level = state.get("risk_level", "read_only")
    if risk_level in BLOCKED_RISK:
        return {
            "allowed": False,
            "error_code": "TOOL_REQUIRES_APPROVAL"
            if risk_level == "approval_required"
            else "TOOL_POLICY_BLOCKED",
            "block_reason": f"Tool '{state.get('tool_name')}' is blocked by Phase 3 safety policy.",
        }
    return {"allowed": True, "block_reason": None, "error_code": None}
