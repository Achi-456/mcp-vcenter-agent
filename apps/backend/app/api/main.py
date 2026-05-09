import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.api.routes import audit, connections, health, sessions, tools
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.chat import ChatRequest

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="vCenter Agentic Ops API", version="0.1.0-rebuild")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://infra-agent-console.dclab.local",
        "https://app.dclab.local",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tools.router)
app.include_router(connections.router)
app.include_router(audit.router)
app.include_router(sessions.router)


@app.get("/health")
async def compatibility_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def compatibility_ready() -> dict[str, Any]:
    return {
        "status": "ready",
        "backend": "ok",
        "mode": "fastapi-foundation-pack",
    }


@app.get("/api/v1/platform/status")
async def platform_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "services": [
            {"name": "backend", "status": "ok", "detail": "FastAPI gateway online"},
            {"name": "agent-engine", "status": "planned", "detail": "Phase rebuild placeholder"},
            {"name": "mcp", "status": "planned", "detail": "MCP placeholder online after deploy"},
            {"name": "postgres", "status": "external", "detail": "Use /api/v1/health/services"},
            {"name": "redis", "status": "external", "detail": "Use /api/v1/health/services"},
        ],
    }


@app.post("/api/v1/chat/stream")
@app.post("/api/v1/agent/run")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())

    async def events():
        payloads = [
            {"type": "session", "session_id": session_id},
            {
                "type": "node",
                "node": "gateway",
                "output": {"message": request.message, "status": "received"},
            },
            {
                "type": "final",
                "content": "Hi, I'm your vCenter Agent. How can I help you with your infrastructure today?",
            },
            {"type": "done"},
        ]
        for payload in payloads:
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.websocket("/ws")
async def websocket_echo(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "message": message})
    except WebSocketDisconnect:
        return
