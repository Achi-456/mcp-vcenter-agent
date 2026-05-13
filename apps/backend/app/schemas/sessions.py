from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatSessionSummary(BaseModel):
    id: str
    session_id: str
    title: str | None = None
    status: str
    last_message_preview: str | None = None
    last_intent: str | None = None
    last_entities: dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0
    run_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    metadata: dict[str, Any] = Field(default_factory=dict)

