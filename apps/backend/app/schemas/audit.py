from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventCreate(BaseModel):
    event_type: str
    actor: str | None = None
    target: str | None = None
    action: str
    status: str
    error_code: str | None = None
    risk_level: str | None = None
    metadata: dict[str, Any] = {}


class AuditEventRead(AuditEventCreate):
    id: int
    created_at: datetime
