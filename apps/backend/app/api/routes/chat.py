import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.db.session import get_session_factory
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatRequest
from app.services.agent_client import AgentClient
from app.services.conversation_context import build_conversation_context

router = APIRouter(tags=["chat"])


def agent_client_dep() -> AgentClient:
    return AgentClient()


@router.post("/api/v1/chat/stream")
@router.post("/api/v1/agent/run")
async def chat_stream(
    request: ChatRequest,
    agent_client: Annotated[AgentClient, Depends(agent_client_dep)],
) -> StreamingResponse:
    return StreamingResponse(
        _persistent_stream(request, agent_client),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _persistent_stream(request: ChatRequest, agent_client: AgentClient) -> AsyncIterator[str]:
    session_factory = get_session_factory()
    if session_factory is None:
        async for chunk in agent_client.stream_run(request):
            yield chunk
        return

    session_id = request.session_id
    context: dict[str, Any] | None = None
    try:
        async with session_factory() as db:
            repo = ChatRepository(db)
            session = await repo.get_session(session_id) if session_id else None
            if session is None:
                session = await repo.create_session(session_id=session_id, title=_title_from_message(request.message))
            session_id = session.id
            context = await build_conversation_context(repo, session)
            await repo.add_message(
                session_id=session_id,
                role="user",
                content=request.message,
                metadata={"source": "chat_stream"},
            )
            await db.commit()
    except Exception:
        async for chunk in agent_client.stream_run(request):
            yield chunk
        return

    stream_request = request.model_copy(update={"session_id": session_id, "conversation_context": context})
    collector = _StreamCollector(session_id=session_id, user_message=request.message)
    async for chunk in agent_client.stream_run(stream_request):
        collector.feed(chunk)
        yield chunk

    try:
        async with session_factory() as db:
            repo = ChatRepository(db)
            await collector.persist(repo)
            await db.commit()
    except Exception:
        return


class _StreamCollector:
    def __init__(self, *, session_id: str, user_message: str) -> None:
        self.session_id = session_id
        self.user_message = user_message
        self.buffer = ""
        self.events: list[dict[str, Any]] = []
        self.run_id: str | None = None

    def feed(self, chunk: str) -> None:
        self.buffer += chunk.replace("\r\n", "\n")
        while "\n\n" in self.buffer:
            frame, self.buffer = self.buffer.split("\n\n", 1)
            event = _parse_frame(frame)
            if event:
                if event.get("type") == "start":
                    self.run_id = _string(event.get("run_id")) or self.run_id
                self.events.append(event)

    async def persist(self, repo: ChatRepository) -> None:
        final = _last_event(self.events, "final")
        intent = _last_event(self.events, "intent")
        error = _last_event(self.events, "error")
        run_id = self.run_id or _string(final.get("run_id") if final else None)
        if run_id:
            await repo.start_run(
                run_id=run_id,
                session_id=self.session_id,
                input_json={"message": self.user_message},
            )
        for tool_call, tool_result in _tool_pairs(self.events):
            await repo.add_tool_call(
                run_id=run_id,
                session_id=self.session_id,
                tool_name=_string(tool_call.get("tool")) or "unknown",
                risk_level=_string(tool_call.get("risk_level")) or "read_only",
                status="completed" if not tool_result or tool_result.get("ok", True) else "failed",
                input_summary=_string(tool_call.get("input_summary")),
                output_summary=_string(tool_result.get("output_summary")) if tool_result else None,
                error_code=_string(tool_result.get("error_code")) if tool_result else None,
                summary_json={"tool_call": tool_call, "tool_result": tool_result or {}},
            )
        if final:
            content = _string(final.get("content")) or ""
            await repo.add_message(
                session_id=self.session_id,
                role="assistant",
                content=content,
                metadata={"final": _metadata(final), "intent": _metadata(intent or {})},
            )
            await repo.update_session_context(
                self.session_id,
                last_intent=_string((intent or {}).get("task_type")),
                last_entities=_entities_from_intent(intent or {}),
                preview=content,
            )
        if run_id:
            await repo.complete_run(
                run_id=run_id,
                status="failed" if error else "completed",
                output_json={"final": _metadata(final or {}), "intent": _metadata(intent or {}), "error": _metadata(error or {})},
                error_code=_string(error.get("error_code")) if error else None,
                final_answer_source=_string(final.get("final_answer_source")) if final else None,
                llm_used=bool(final.get("llm_used")) if final else False,
            )


def _parse_frame(frame: str) -> dict[str, Any] | None:
    data_lines = [line[5:].strip() for line in frame.split("\n") if line.startswith("data:")]
    if not data_lines:
        return None
    raw = "\n".join(data_lines)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _last_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    return next((event for event in reversed(events) if event.get("type") == event_type), None)


def _tool_pairs(events: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    pending: dict[str, Any] | None = None
    for event in events:
        if event.get("type") == "tool_call":
            pending = event
        elif event.get("type") == "tool_result" and pending:
            pairs.append((pending, event))
            pending = None
    if pending:
        pairs.append((pending, None))
    return pairs


def _title_from_message(message: str) -> str:
    text = " ".join(message.split())
    return text[:80]


def _entities_from_intent(intent: dict[str, Any]) -> dict[str, str]:
    object_type = _string(intent.get("object_type"))
    entity = _string(intent.get("entity"))
    if object_type in {"vm", "host", "datastore"} and entity:
        return {object_type: entity}
    return {}


def _metadata(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key != "content"}


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
