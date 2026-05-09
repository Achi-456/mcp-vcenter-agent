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

            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
            initial_state: dict[str, object] = {
                "session_id": session_id,
                "user_message": request.message,
                "messages": [HumanMessage(content=request.message)],
                "provider": request.provider,
                "model": request.model,
                "allow_high_risk": request.allow_high_risk,
                "page_context": request.page_context,
            }

            yield _sse("start", {"session_id": session_id, "run_id": run_id})
            
            # Keep track of last message count so we only emit new ones
            last_message_count = len(initial_state["messages"])

            async for event in graph.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue

                    status = node_output.get("status", "")
                    messages = node_output.get("messages", [])
                    
                    if not messages:
                        continue
                        
                    # Find new messages
                    if isinstance(messages, list):
                        new_messages = messages
                    else:
                        new_messages = [messages]
                        
                    for msg in new_messages:
                        if isinstance(msg, AIMessage):
                            # AIMessage might have tool calls or just final text
                            if msg.tool_calls:
                                yield _sse("intent", {"intent": "using_tools"})
                                for tc in msg.tool_calls:
                                    yield _sse("tool_call", {"tool": tc["name"], "status": "running", "args": tc["args"]})
                            elif msg.content:
                                yield _sse("llm_start", {"provider": request.provider, "model": request.model})
                                yield _sse("final", {"content": msg.content})
                                
                        elif isinstance(msg, ToolMessage):
                            # Tool finished
                            yield _sse("tool_result", {
                                "tool": msg.name,
                                "status": "success" if "ok" in msg.content or "true" in msg.content.lower() else "completed",
                                "summary": "Tool finished execution"
                            })

            yield _sse("done", {})

        except Exception as exc:
            import traceback
            traceback.print_exc()
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
