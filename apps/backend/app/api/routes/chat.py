import json
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/chat")

AGENT_ENGINE_URL = os.getenv(
    "AGENT_ENGINE_URL",
    "http://agent-engine.agentic-agents.svc.cluster.local:8080",
)


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    allow_high_risk: bool = False
    page_context: dict | None = None


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        try:
            timeout = httpx.Timeout(300.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{AGENT_ENGINE_URL}/stream",
                    json={
                        "session_id": request.session_id,
                        "message": request.message,
                        "provider": request.provider,
                        "model": request.model,
                        "allow_high_risk": request.allow_high_risk,
                        "page_context": request.page_context,
                    },
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        payload = {"type": "error", "message": body.decode()}
                        yield f"data: {json.dumps(payload)}\n\n"
                        return
                    async for chunk in response.aiter_text():
                        yield chunk
        except Exception as exc:
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions")
async def list_sessions():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{AGENT_ENGINE_URL}/sessions")
            return resp.json()
    except Exception as exc:
        return {"items": [], "error": str(exc)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{AGENT_ENGINE_URL}/sessions/{session_id}")
            return resp.json()
    except Exception as exc:
        return {"error": str(exc)}
