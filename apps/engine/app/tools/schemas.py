from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    APPROVAL_REQUIRED = "approval_required"
    DESTRUCTIVE = "destructive"


class ToolCategory(str, Enum):
    INVENTORY = "Inventory & Information"
    VM_MANAGEMENT = "VM Management"
    SNAPSHOT = "VM Snapshots"
    HOST_MANAGEMENT = "Host Management"
    MONITORING = "Monitoring & Events"
    CONTEXT = "Context Helpers"
    GENERAL = "General & Utility"


class ToolSpec(BaseModel):
    name: str
    display_name: str
    description: str
    category: ToolCategory = ToolCategory.INVENTORY
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    enabled: bool = True
    implemented: bool = True
    requires_approval: bool = False
    cache_ttl_seconds: int = 30
    backend_endpoint: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
