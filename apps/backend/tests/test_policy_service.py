from app.core.errors import ErrorCode
from app.schemas.tools import RiskLevel, ToolSpec
from app.services.policy_service import PolicyService


def make_tool(
    *,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    enabled: bool = True,
    implemented: bool = True,
) -> ToolSpec:
    return ToolSpec(
        name="test_tool",
        display_name="Test Tool",
        description="Test",
        domain="test",
        category="test",
        agent="test_agent",
        backend="test_backend",
        risk_level=risk_level,
        enabled=enabled,
        implemented=implemented,
        requires_approval=risk_level == RiskLevel.APPROVAL_REQUIRED,
        input_schema={},
        output_schema={},
    )


def test_read_only_implemented_tool_allowed() -> None:
    decision = PolicyService().evaluate(make_tool())

    assert decision.allowed is True
    assert decision.error_code is None


def test_low_risk_blocked() -> None:
    decision = PolicyService().evaluate(make_tool(risk_level=RiskLevel.LOW_RISK))

    assert decision.allowed is False
    assert decision.error_code == ErrorCode.TOOL_POLICY_BLOCKED


def test_approval_required_blocked() -> None:
    decision = PolicyService().evaluate(make_tool(risk_level=RiskLevel.APPROVAL_REQUIRED))

    assert decision.allowed is False
    assert decision.error_code == ErrorCode.TOOL_REQUIRES_APPROVAL


def test_destructive_blocked() -> None:
    decision = PolicyService().evaluate(make_tool(risk_level=RiskLevel.DESTRUCTIVE))

    assert decision.allowed is False
    assert decision.error_code == ErrorCode.TOOL_POLICY_BLOCKED


def test_disabled_blocked() -> None:
    decision = PolicyService().evaluate(make_tool(enabled=False))

    assert decision.allowed is False
    assert decision.error_code == ErrorCode.TOOL_DISABLED


def test_unimplemented_blocked() -> None:
    decision = PolicyService().evaluate(make_tool(implemented=False))

    assert decision.allowed is False
    assert decision.error_code == ErrorCode.TOOL_NOT_IMPLEMENTED
