from typing import Any

from pydantic import BaseModel


class ResponseMetadata(BaseModel):
    source: str
    cached: bool = False
    collected_at: str


class SuccessEnvelope(BaseModel):
    ok: bool = True
    data: Any
    metadata: ResponseMetadata


class ErrorEnvelope(BaseModel):
    ok: bool = False
    error_code: str
    message: str
    details: dict[str, Any]
