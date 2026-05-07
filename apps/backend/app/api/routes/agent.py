import os
import json
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/agent")

AGENT_ENGINE_URL = os.getenv(
    "AGENT_ENGINE_URL",
    "http://agent-engine.agentic-agents.svc.cluster.local:8080",
)


class RunRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)


@router.post("/run")
async def proxy_run(request: RunRequest) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        try:
            timeout = httpx.Timeout(300.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{AGENT_ENGINE_URL}/run",
                    json=request.model_dump(),
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


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{AGENT_ENGINE_URL}/sessions/{session_id}")

    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text}

    return JSONResponse(payload, status_code=response.status_code)
