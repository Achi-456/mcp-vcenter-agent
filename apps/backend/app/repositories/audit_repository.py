from sqlalchemy import desc, select

from app.db.models import AuditEvent
from app.db.session import get_session_factory
from app.schemas.audit import AuditEventCreate


class AuditRepository:
    async def create(self, event: AuditEventCreate) -> AuditEvent | None:
        session_factory = get_session_factory()
        if session_factory is None:
            return None
        async with session_factory() as session:
            row = AuditEvent(
                event_type=event.event_type,
                actor=event.actor,
                target=event.target,
                action=event.action,
                status=event.status,
                error_code=event.error_code,
                risk_level=event.risk_level,
                metadata_json=event.metadata,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def recent(self, *, limit: int = 50) -> list[AuditEvent]:
        session_factory = get_session_factory()
        if session_factory is None:
            return []
        async with session_factory() as session:
            result = await session.execute(
                select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
            )
            return list(result.scalars().all())
