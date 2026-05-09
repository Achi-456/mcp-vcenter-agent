import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


app = FastAPI(title="vCenter Agent Engine", version="0.1.0-rebuild")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ready",
            "engine": "ok",
            "langgraph": "placeholder",
            "db": "not-configured-in-baseline",
            "redis": "not-configured-in-baseline",
        }
    )


@app.post("/run")
@app.post("/api/v1/agent/run")
async def run_agent(request: RunRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())

    async def events():
        for payload in (
            {"type": "session", "session_id": session_id},
            {"type": "node", "node": "load_context", "output": {"status": "baseline"}},
            {
                "type": "node",
                "node": "echo_node",
                "output": {
                    "final_answer": (
                        "Agent engine rebuild baseline is online. "
                        f"Message received: {request.message}"
                    )
                },
            },
            {"type": "done"},
        ):
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "found": False,
        "values": {},
        "next": [],
        "metadata": {"mode": "clean-rebuild-baseline"},
    }

