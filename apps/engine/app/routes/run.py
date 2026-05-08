import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.runtime import runtime

router = APIRouter()


class RunRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)


@router.post("/run")
async def run_agent(request: RunRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())

    async def event_stream() -> AsyncIterator[str]:
        try:
            graph = await runtime.graph()
            config = {"configurable": {"thread_id": session_id}}
            initial_state = {
                "session_id": session_id,
                "user_message": request.message,
                "messages": [],
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "allow_high_risk": False,
                "page_context": None,
                "turn": 0,
                "intent": "",
                "entity": None,
                "safety_verdict": None,
                "selected_tools": [],
                "tool_results": [],
                "final_answer": None,
                "suggested_next": None,
                "error": None,
                "status": "thinking",
            }

            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            async for event in graph.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    payload = {
                        "type": "node",
                        "node": node_name,
                        "output": node_output,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

