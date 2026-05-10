from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import audit_dep, secret_store_dep, settings_dep, vcenter_session_dep
from app.core.responses import success_response
from app.schemas.audit import AuditEventCreate
from app.services.audit_service import AuditService
from app.services.secret_store import SecretStore
from app.services.vcenter_session import VCenterError, VCenterSession
from app.core.config import Settings

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


@router.get("")
async def connections(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    return success_response(
        [{"name": "vcenter", "secret_name": settings.vcenter_secret_name}],
        source="connection_profiles",
    )


@router.get("/vcenter/status")
async def vcenter_status(
    settings: Settings = Depends(settings_dep),
    secrets: SecretStore = Depends(secret_store_dep),
) -> dict[str, Any]:
    exists = await secrets.exists(settings.vcenter_secret_name)
    keys = await secrets.read_keys(settings.vcenter_secret_name) if exists else []
    return success_response(
        {
            "name": "vcenter",
            "configured": exists,
            "status": "configured" if exists else "not_configured",
            "detail": "Secret reference found" if exists else "Secret reference not found",
            "secret_name": settings.vcenter_secret_name,
            "secret_keys": keys,
        },
        source="kubernetes_secret",
    )


@router.post("/vcenter/test")
async def test_vcenter(
    settings: Settings = Depends(settings_dep),
    audit: AuditService = Depends(audit_dep),
    session: VCenterSession = Depends(vcenter_session_dep),
) -> dict[str, Any]:
    try:
        result = await session.test_connection()
        status = "connected"
        error_code = None
    except VCenterError as exc:
        result = {"status": "error", "error_code": exc.error_code, "message": exc.message}
        status = "error"
        error_code = str(exc.error_code)

    await audit.record(
        AuditEventCreate(
            event_type="connection_test",
            target="vcenter",
            action="test",
            status=status,
            error_code=error_code,
            metadata={"secret_name": settings.vcenter_secret_name},
        )
    )
    return success_response({"name": "vcenter", **result}, source="connection_service")


@router.post("/vcenter/reconnect")
async def reconnect_vcenter(
    settings: Settings = Depends(settings_dep),
    audit: AuditService = Depends(audit_dep),
    session: VCenterSession = Depends(vcenter_session_dep),
) -> dict[str, Any]:
    try:
        result = await session.reconnect()
        status = "reconnected"
        error_code = None
    except VCenterError as exc:
        result = {"status": "error", "error_code": exc.error_code, "message": exc.message}
        status = "error"
        error_code = str(exc.error_code)

    await audit.record(
        AuditEventCreate(
            event_type="connection_reconnect",
            target="vcenter",
            action="reconnect",
            status=status,
            error_code=error_code,
            metadata={"secret_name": settings.vcenter_secret_name},
        )
    )
    return success_response({"name": "vcenter", **result}, source="connection_service")
