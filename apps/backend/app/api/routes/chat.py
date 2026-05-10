from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.agent_client import AgentClient

router = APIRouter(tags=["chat"])


def agent_client_dep() -> AgentClient:
    return AgentClient()


@router.post("/api/v1/chat/stream")
@router.post("/api/v1/agent/run")
async def chat_stream(
    request: ChatRequest,
    agent_client: Annotated[AgentClient, Depends(agent_client_dep)],
) -> StreamingResponse:
    return StreamingResponse(
        agent_client.stream_run(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
