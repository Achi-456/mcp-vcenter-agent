from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.check import check_dependencies

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    results = await check_dependencies()
    ready_status = all(value == "ok" for value in results.values())
    status_code = 200 if ready_status else 503
    payload = {"status": "ready" if ready_status else "degraded", **results}
    return JSONResponse(payload, status_code=status_code)
