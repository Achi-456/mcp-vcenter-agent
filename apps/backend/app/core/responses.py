from datetime import UTC, datetime
from typing import Any

from app.core.errors import ErrorCode


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def success_response(
    data: Any,
    *,
    source: str,
    cached: bool = False,
    collected_at: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "metadata": {
            "source": source,
            "cached": cached,
            "collected_at": collected_at or utc_now_iso(),
        },
    }


def error_response(
    error_code: ErrorCode | str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error_code": str(error_code),
        "message": message,
        "details": details or {},
    }
