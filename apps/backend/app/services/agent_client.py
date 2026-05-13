import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings
from app.schemas.chat import ChatRequest


class AgentClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_settings().agent_engine_url).rstrip("/")

    async def stream_run(self, request: ChatRequest) -> AsyncIterator[str]:
        payload = request.model_dump(exclude_none=True)
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/run",
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if chunk:
                            yield chunk
        except Exception as exc:
            yield _sse({"type": "error", "error_code": "AGENT_ENGINE_UNAVAILABLE", "message": str(exc)})
            yield _sse({"type": "done"})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"
