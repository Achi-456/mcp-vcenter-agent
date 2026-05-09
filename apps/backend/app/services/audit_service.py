from typing import Any

from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditEventCreate


SECRET_MARKERS = ("password", "api_key", "token", "secret")


def redact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in metadata.items():
        if any(marker in key.lower() for marker in SECRET_MARKERS):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self.repository = repository or AuditRepository()

    async def record(self, event: AuditEventCreate) -> Any | None:
        safe_event = event.model_copy(update={"metadata": redact_metadata(event.metadata)})
        return await self.repository.create(safe_event)

    async def record_tool_decision(
        self,
        *,
        tool_name: str,
        status: str,
        risk_level: str | None,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any | None:
        return await self.record(
            AuditEventCreate(
                event_type="tool_call",
                target=tool_name,
                action="policy_decision",
                status=status,
                error_code=error_code,
                risk_level=risk_level,
                metadata=metadata or {},
            )
        )

    async def recent(self, *, limit: int = 50) -> list[Any]:
        return await self.repository.recent(limit=limit)
