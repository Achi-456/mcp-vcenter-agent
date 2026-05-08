import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.runtime import runtime

router = APIRouter()


class StreamRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    allow_high_risk: bool = False
    page_context: dict | None = None


@router.post("/stream")
async def stream_agent(request: StreamRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    async def event_stream() -> AsyncIterator[str]:
        try:
            graph = await runtime.graph()
            config = {"configurable": {"thread_id": session_id}}

            initial_state = {
                "session_id": session_id,
                "user_message": request.message,
                "messages": [],
                "provider": request.provider,
                "model": request.model,
                "allow_high_risk": request.allow_high_risk,
                "page_context": request.page_context,
                "turn": 0,
                "safety_verdict": None,
                "selected_tools": [],
                "tool_results": [],
                "final_answer": None,
                "error": None,
                "status": "thinking",
            }

            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'run_id': run_id})}\n\n"

            async for event in graph.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue

                    status = node_output.get("status", "")

                    if status == "blocked":
                        verdict = node_output.get("safety_verdict", {})
                        payload = {
                            "type": "blocked",
                            "reason": verdict.get("reason", "HIGH_RISK_ACTION"),
                            "message": verdict.get("message", "Action blocked for safety."),
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return

                    if node_name == "select_tools":
                        tools = node_output.get("selected_tools", [])
                        for tool_name in tools:
                            payload = {
                                "type": "tool_call",
                                "tool": tool_name,
                                "status": "running",
                                "args": {},
                            }
                            yield f"data: {json.dumps(payload)}\n\n"

                    if node_name == "execute_tools":
                        tool_results = node_output.get("tool_results", [])
                        for tr in tool_results:
                            payload = {
                                "type": "tool_result",
                                "tool": tr.get("tool", "unknown"),
                                "status": tr.get("status", "error"),
                                "summary": tr.get("summary", ""),
                            }
                            yield f"data: {json.dumps(payload)}\n\n"

                    if node_name == "generate_answer":
                        final_answer = node_output.get("final_answer", "")
                        if final_answer:
                            yield f"data: {json.dumps({'type': 'final', 'content': final_answer})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
