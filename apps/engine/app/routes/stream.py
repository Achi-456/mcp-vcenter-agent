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

            initial_state: dict[str, object] = {
                "session_id": session_id,
                "user_message": request.message,
                "messages": [],
                "provider": request.provider,
                "model": request.model,
                "allow_high_risk": request.allow_high_risk,
                "page_context": request.page_context,
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

            yield _sse("start", {"session_id": session_id, "run_id": run_id})

            async for event in graph.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue

                    status = node_output.get("status", "")

                    if status == "blocked":
                        verdict = node_output.get("safety_verdict", {})
                        yield _sse("blocked", {
                            "reason": verdict.get("reason", "HIGH_RISK_ACTION"),
                            "message": verdict.get("message", "Action blocked for safety."),
                        })
                        yield _sse("done", {})
                        return

                    if node_name == "classify_request":
                        intent = node_output.get("intent", "")
                        entity = node_output.get("entity")
                        yield _sse("intent", {"intent": intent, "entity": entity})
                        yield _sse("safety_check", {"passed": True})

                    if node_name == "select_tools":
                        tools = node_output.get("selected_tools", [])
                        for tool_name in tools:
                            yield _sse("tool_call", {"tool": tool_name, "status": "running", "args": {}})

                    if node_name == "execute_tools":
                        tool_results = node_output.get("tool_results", [])
                        for tr in tool_results:
                            yield _sse("tool_result", {
                                "tool": tr.get("tool", "unknown"),
                                "status": tr.get("status", "error"),
                                "summary": tr.get("summary", ""),
                                "data_count": _get_data_count(tr.get("data", {})),
                            })

                    if node_name == "generate_answer":
                        final_answer = node_output.get("final_answer", "")
                        suggested_next = node_output.get("suggested_next")

                        if final_answer:
                            yield _sse("final", {"content": final_answer})

                        if suggested_next:
                            yield _sse("suggested_next_step", {"content": suggested_next})

            yield _sse("done", {})

        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


def _get_data_count(data: dict) -> int | None:
    if not data:
        return None
    if "items" in data:
        return data.get("count", len(data["items"]))
    if "vms" in data and isinstance(data["vms"], list):
        return len(data["vms"])
    if "count" in data:
        return data["count"]
    if "total" in data:
        return data["total"]
    return None
