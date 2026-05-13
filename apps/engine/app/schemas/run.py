from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    conversation_context: dict[str, Any] | None = None
