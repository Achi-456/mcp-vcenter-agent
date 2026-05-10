from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep, cache_dep, policy_dep, tool_registry_dep, vcenter_monitoring_dep
from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService
from app.services.vcenter_monitoring_service import VCenterMonitoringService

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/alarms")
async def alarms(
    refresh: bool = Query(default=False),
    service: VCenterMonitoringService = Depends(vcenter_monitoring_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_active_alarms",
        operation=service.get_active_alarms,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )


@router.get("/events")
async def events(
    limit: int = Query(default=50, ge=1, le=200),
    refresh: bool = Query(default=False),
    service: VCenterMonitoringService = Depends(vcenter_monitoring_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_recent_events",
        operation=lambda: service.get_recent_events(limit=limit),
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        inputs={"limit": limit},
    )
