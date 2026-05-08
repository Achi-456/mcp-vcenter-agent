from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.routes.agent import router as agent_router
from app.api.routes.chat import router as chat_router
from app.api.routes.connections import router as connections_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.context import router as context_router
from app.api.routes.llm import router as llm_router
from app.db.check import check_dependencies

app = FastAPI(title="vCenter Agentic Ops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://infra-agent-console.dclab.local", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(connections_router)
app.include_router(inventory_router)
app.include_router(monitoring_router)
app.include_router(context_router)
app.include_router(llm_router)


@app.get("/api/v1/tools")
async def tools_proxy():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://mcp-server.agentic-app.svc.cluster.local:8001/tools")
            return resp.json()
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"tools": [], "error": "MCP server unreachable"}, status_code=503)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    results = await check_dependencies()
    ready_status = all(value == "ok" for value in results.values())
    status_code = 200 if ready_status else 503
    payload = {"status": "ready" if ready_status else "degraded", **results}
    return JSONResponse(payload, status_code=status_code)


@app.get("/api/v1/chat/stream-test")
async def stream_test() -> StreamingResponse:
    async def events():
        for token in ("phase", "07", "sse", "ok"):
            yield f"event: token\ndata: {token}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.websocket("/ws")
async def websocket_echo(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"status": "ok", "message": "websocket connected"})
    await websocket.close()
