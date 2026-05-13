from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun, ChatMessage, ChatSession, ToolCall, utc_now


def new_session_id() -> str:
    return str(uuid.uuid4())


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self, *, session_id: str | None = None, title: str | None = None) -> ChatSession:
        item = ChatSession(id=session_id or new_session_id(), title=title, status="active")
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_session(self, session_id: str) -> ChatSession | None:
        return await self.session.get(ChatSession, session_id)

    async def require_session(self, session_id: str) -> ChatSession:
        item = await self.get_session(session_id)
        if item is None:
            raise KeyError(session_id)
        return item

    async def list_sessions(self, *, limit: int = 50, offset: int = 0) -> list[tuple[ChatSession, int, int]]:
        message_count = (
            select(ChatMessage.session_id, func.count(ChatMessage.id).label("message_count"))
            .group_by(ChatMessage.session_id)
            .subquery()
        )
        run_count = (
            select(AgentRun.session_id, func.count(AgentRun.id).label("run_count"))
            .group_by(AgentRun.session_id)
            .subquery()
        )
        stmt = (
            select(
                ChatSession,
                func.coalesce(message_count.c.message_count, 0),
                func.coalesce(run_count.c.run_count, 0),
            )
            .outerjoin(message_count, message_count.c.session_id == ChatSession.id)
            .outerjoin(run_count, run_count.c.session_id == ChatSession.id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.execute(stmt)
        return [(row[0], int(row[1]), int(row[2])) for row in rows.all()]

    async def list_messages(self, session_id: str, *, limit: int = 100) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())

    async def recent_messages(self, session_id: str, *, limit: int = 10) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return list(reversed(rows.scalars().all()))

    async def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        item = ChatMessage(session_id=session_id, role=role, content=content, metadata_json=metadata or {})
        self.session.add(item)
        await self.touch_session(session_id, preview=content)
        await self.session.flush()
        return item

    async def start_run(self, *, run_id: str, session_id: str, input_json: dict[str, Any]) -> AgentRun:
        item = AgentRun(
            id=run_id,
            session_id=session_id,
            status="started",
            input_json=input_json,
            started_at=utc_now(),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        output_json: dict[str, Any] | None = None,
        error_code: str | None = None,
        final_answer_source: str | None = None,
        llm_used: bool = False,
    ) -> None:
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            return
        run.status = status
        run.output_json = output_json
        run.error_code = error_code
        run.final_answer_source = final_answer_source
        run.llm_used = llm_used
        run.completed_at = utc_now()
        run.updated_at = utc_now()

    async def add_tool_call(
        self,
        *,
        run_id: str | None,
        session_id: str,
        tool_name: str,
        risk_level: str,
        status: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
        error_code: str | None = None,
        summary_json: dict[str, Any] | None = None,
    ) -> ToolCall:
        item = ToolCall(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            risk_level=risk_level,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            error_code=error_code,
            summary_json=summary_json,
            metadata_json={},
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def latest_run(self, session_id: str) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(AgentRun.session_id == session_id)
            .order_by(desc(AgentRun.created_at))
            .limit(1)
        )
        rows = await self.session.execute(stmt)
        return rows.scalars().first()

    async def latest_tool_summaries(self, session_id: str, *, limit: int = 10) -> list[ToolCall]:
        stmt = (
            select(ToolCall)
            .where(ToolCall.session_id == session_id)
            .order_by(desc(ToolCall.created_at), desc(ToolCall.id))
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())

    async def update_session_context(
        self,
        session_id: str,
        *,
        last_intent: str | None = None,
        last_entities: dict[str, Any] | None = None,
        preview: str | None = None,
    ) -> None:
        item = await self.get_session(session_id)
        if item is None:
            return
        if last_intent:
            item.last_intent = last_intent
        if last_entities is not None:
            item.last_entities_json = last_entities
        await self.touch_session(session_id, preview=preview)

    async def touch_session(self, session_id: str, *, preview: str | None = None) -> None:
        item = await self.get_session(session_id)
        if item is None:
            return
        item.updated_at = utc_now()
        if preview:
            item.last_message_preview = _preview(preview)
            if not item.title:
                item.title = _preview(preview, max_length=80)


def _preview(value: str, *, max_length: int = 180) -> str:
    text = " ".join(value.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def datetime_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

