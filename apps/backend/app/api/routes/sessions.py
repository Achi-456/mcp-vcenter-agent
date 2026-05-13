from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.core.responses import success_response
from app.db.session import get_session_factory
from app.repositories.chat_repository import ChatRepository
from app.schemas.sessions import ChatSessionCreate

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    session_factory = _require_session_factory()
    async with session_factory() as db:
        repo = ChatRepository(db)
        rows = await repo.list_sessions(limit=limit, offset=offset)
        return success_response([_session_summary(item, message_count, run_count) for item, message_count, run_count in rows], source="postgres")


@router.post("")
async def create_session(payload: Annotated[ChatSessionCreate, Body()] = ChatSessionCreate()) -> dict[str, Any]:
    session_factory = _require_session_factory()
    async with session_factory() as db:
        repo = ChatRepository(db)
        item = await repo.create_session(title=payload.title)
        await db.commit()
        return success_response(_session_summary(item, 0, 0), source="postgres")


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    session_factory = _require_session_factory()
    async with session_factory() as db:
        repo = ChatRepository(db)
        item = await repo.get_session(session_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        messages = await repo.list_messages(session_id, limit=1)
        latest_run = await repo.latest_run(session_id)
        return success_response(
            {
                **_session_summary(item, len(messages), 1 if latest_run else 0),
                "metadata": item.metadata_json or {},
            },
            source="postgres",
        )


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict[str, Any]:
    session_factory = _require_session_factory()
    async with session_factory() as db:
        repo = ChatRepository(db)
        if await repo.get_session(session_id) is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        messages = await repo.list_messages(session_id, limit=limit)
        return success_response([_message_response(item) for item in messages], source="postgres")


def _require_session_factory():
    session_factory = get_session_factory()
    if session_factory is None:
        raise HTTPException(status_code=503, detail="DB_URL is not configured.")
    return session_factory


def _session_summary(item: Any, message_count: int, run_count: int) -> dict[str, Any]:
    return {
        "id": item.id,
        "session_id": item.id,
        "title": item.title,
        "status": item.status,
        "last_message_preview": item.last_message_preview,
        "last_intent": item.last_intent,
        "last_entities": item.last_entities_json or {},
        "message_count": message_count,
        "run_count": run_count,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _message_response(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "session_id": item.session_id,
        "role": item.role,
        "content": item.content,
        "metadata": item.metadata_json or {},
        "created_at": item.created_at.isoformat(),
    }
