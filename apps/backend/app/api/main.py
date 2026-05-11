from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    audit,
    chat,
    connections,
    context,
    govc,
    health,
    internal_mcp,
    inventory,
    mcp,
    monitoring,
    sessions,
    tools,
    vsphere_rest,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.health_service import HealthService

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
app.include_router(inventory.router)
app.include_router(context.router)
app.include_router(monitoring.router)
app.include_router(mcp.router)
app.include_router(internal_mcp.router)
app.include_router(govc.router)
app.include_router(vsphere_rest.router)
app.include_router(audit.router)
app.include_router(sessions.router)
app.include_router(chat.router)


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
    services = await HealthService().services()
    return {
        "status": "ok",
        "services": [
            {"name": "backend", "status": "ok", "detail": "FastAPI gateway online"},
            {"name": "agent-engine", **services.get("agent_engine", {})},
            {"name": "mcp", **services.get("mcp_gateway", {})},
            {"name": "postgres", **services.get("postgres", {})},
            {"name": "redis", **services.get("redis", {})},
        ],
    }


@app.websocket("/ws")
async def websocket_echo(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "message": message})
    except WebSocketDisconnect:
        return
