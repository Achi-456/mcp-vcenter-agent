import json
from typing import Any


def event_payload(event_type: str, **fields: Any) -> dict[str, Any]:
    return {"type": event_type, **fields}


def sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
