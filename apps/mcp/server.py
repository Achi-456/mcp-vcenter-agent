from fastapi import FastAPI

app = FastAPI(title="vCenter MCP Server")


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "tools": [], "resources": [], "prompts": []}
