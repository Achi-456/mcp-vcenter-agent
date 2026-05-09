from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import audit_dep, secret_store_dep, settings_dep
from app.core.responses import success_response
from app.schemas.audit import AuditEventCreate
from app.services.audit_service import AuditService
from app.services.secret_store import SecretStore
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
    secrets: SecretStore = Depends(secret_store_dep),
    audit: AuditService = Depends(audit_dep),
) -> dict[str, Any]:
    exists = await secrets.exists(settings.vcenter_secret_name)
    await audit.record(
        AuditEventCreate(
            event_type="connection_test",
            target="vcenter",
            action="test",
            status="configured" if exists else "not_configured",
            metadata={"secret_name": settings.vcenter_secret_name},
        )
    )
    return success_response(
        {
            "name": "vcenter",
            "status": "configured" if exists else "not_configured",
            "detail": "Secret reference found; live pyVmomi test is not implemented in Phase 1."
            if exists
            else "Secret reference not found.",
        },
        source="connection_service",
    )


@router.post("/vcenter/reconnect")
async def reconnect_vcenter(
    settings: Settings = Depends(settings_dep),
    audit: AuditService = Depends(audit_dep),
) -> dict[str, Any]:
    await audit.record(
        AuditEventCreate(
            event_type="connection_reconnect",
            target="vcenter",
            action="reconnect",
            status="accepted",
            metadata={"secret_name": settings.vcenter_secret_name},
        )
    )
    return success_response(
        {
            "name": "vcenter",
            "status": "accepted",
            "detail": "Reconnect requested; persistent vCenter sessions are not used in Phase 1.",
        },
        source="connection_service",
    )
