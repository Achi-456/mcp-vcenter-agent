from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    APPROVAL_REQUIRED = "approval_required"
    DESTRUCTIVE = "destructive"


class ToolSpec(BaseModel):
    name: str
    display_name: str
    description: str
    domain: str
    category: str
    agent: str
    backend: str
    risk_level: RiskLevel
    enabled: bool
    implemented: bool
    requires_approval: bool
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    mcp_server: str | None = None


class PolicyDecision(BaseModel):
    allowed: bool
    error_code: str | None = None
    message: str
    tool_name: str
    risk_level: RiskLevel | None = None
