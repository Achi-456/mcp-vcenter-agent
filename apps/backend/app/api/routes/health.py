from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import health_dep
from app.core.responses import success_response
from app.services.health_service import HealthService

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
async def health() -> dict[str, Any]:
    return success_response({"status": "ok"}, source="fastapi")


@router.get("/services")
async def services(health_service: HealthService = Depends(health_dep)) -> dict[str, Any]:
    return success_response(await health_service.services(), source="fastapi")
