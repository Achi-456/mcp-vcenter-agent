from app.core.errors import ErrorCode
from app.schemas.tools import PolicyDecision, RiskLevel, ToolSpec


class PolicyService:
    def evaluate(self, tool: ToolSpec) -> PolicyDecision:
        if not tool.enabled:
            return PolicyDecision(
                allowed=False,
                error_code=ErrorCode.TOOL_DISABLED,
                message=f"Tool '{tool.name}' is disabled.",
                tool_name=tool.name,
                risk_level=tool.risk_level,
            )
        if not tool.implemented:
            return PolicyDecision(
                allowed=False,
                error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
                message=f"Tool '{tool.name}' is not implemented in this phase.",
                tool_name=tool.name,
                risk_level=tool.risk_level,
            )
        if tool.risk_level == RiskLevel.READ_ONLY:
            return PolicyDecision(
                allowed=True,
                message=f"Tool '{tool.name}' is allowed.",
                tool_name=tool.name,
                risk_level=tool.risk_level,
            )
        if tool.risk_level == RiskLevel.APPROVAL_REQUIRED:
            return PolicyDecision(
                allowed=False,
                error_code=ErrorCode.TOOL_REQUIRES_APPROVAL,
                message=f"Tool '{tool.name}' requires approval and is blocked in Phase 1.",
                tool_name=tool.name,
                risk_level=tool.risk_level,
            )
        return PolicyDecision(
            allowed=False,
            error_code=ErrorCode.TOOL_POLICY_BLOCKED,
            message=f"Tool '{tool.name}' is blocked by policy.",
            tool_name=tool.name,
            risk_level=tool.risk_level,
        )
