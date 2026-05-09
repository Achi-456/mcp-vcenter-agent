import pytest

from app.schemas.audit import AuditEventCreate
from app.services.audit_service import AuditService


class FakeAuditRepository:
    def __init__(self) -> None:
        self.events = []

    async def create(self, event):
        self.events.append(event)
        return event

    async def recent(self, *, limit: int = 50):
        return self.events[:limit]


@pytest.mark.asyncio
async def test_audit_service_redacts_secret_metadata() -> None:
    repository = FakeAuditRepository()
    service = AuditService(repository=repository)

    await service.record(
        AuditEventCreate(
            event_type="blocked_tool_call",
            target="power_on_vm",
            action="policy_decision",
            status="blocked",
            metadata={"api_key": "dummy-sensitive-value", "safe": "value"},
        )
    )

    event = repository.events[0]
    assert event.metadata["api_key"] == "[REDACTED]"
    assert event.metadata["safe"] == "value"
