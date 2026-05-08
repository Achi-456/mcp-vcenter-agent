from __future__ import annotations

import os

import httpx
import structlog

logger = structlog.get_logger()

FASTAPI_BASE_URL = os.getenv(
    "FASTAPI_INTERNAL_BASE_URL",
    os.getenv(
        "FASTAPI_INTERNAL_URL",
        "http://fastapi.agentic-app.svc.cluster.local:8000",
    ),
)


async def call_backend_get(path: str, params: dict | None = None) -> dict:
    url = f"{FASTAPI_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
    except httpx.TimeoutException:
        return {"ok": False, "error_code": "BACKEND_TIMEOUT", "message": "Backend request timed out."}
    except httpx.ConnectError:
        return {"ok": False, "error_code": "BACKEND_UNREACHABLE", "message": "Backend service is unreachable."}
    except Exception as exc:
        return {"ok": False, "error_code": "BACKEND_ERROR", "message": str(exc)[:200]}

    try:
        data = resp.json()
    except Exception:
        return {"ok": False, "error_code": "BACKEND_INVALID_RESPONSE", "message": resp.text[:300]}

    if resp.status_code >= 400:
        return {
            "ok": False,
            "error_code": data.get("error_code", "BACKEND_ERROR"),
            "message": data.get("message", data.get("detail", "Backend request failed")),
            "status_code": resp.status_code,
        }

    return {"ok": True, "data": data, "status_code": resp.status_code}
