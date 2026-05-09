from typing import Any

from fastapi import APIRouter

from app.core.responses import success_response

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("")
async def list_sessions() -> dict[str, Any]:
    return success_response([], source="postgres")
