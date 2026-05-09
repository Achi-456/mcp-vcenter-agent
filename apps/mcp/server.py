from typing import Any

from fastapi import FastAPI


app = FastAPI(title="vCenter Agentic Ops MCP", version="0.1.0-rebuild")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "tools": [],
        "resources": [],
        "prompts": [],
        "mode": "clean-rebuild-baseline",
    }


@app.get("/tools")
async def tools() -> dict[str, list[Any]]:
    return {"tools": []}


@app.get("/resources")
async def resources() -> dict[str, list[Any]]:
    return {"resources": []}


@app.get("/prompts")
async def prompts() -> dict[str, list[Any]]:
    return {"prompts": []}

