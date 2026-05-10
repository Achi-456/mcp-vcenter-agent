from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep, cache_dep, govc_dep, policy_dep, tool_registry_dep
from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.govc_service import GovcService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService

router = APIRouter(prefix="/api/v1/govc", tags=["govc"])


@router.get("/about")
async def about(
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_about",
        operation=service.about,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        source="govc",
    )


@router.get("/vm-info")
async def vm_info(
    name: str = Query(min_length=1),
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_vm_info",
        operation=lambda: service.vm_info(name),
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        inputs={"name": name},
        source="govc",
    )


@router.get("/host-info")
async def host_info(
    name: str = Query(min_length=1),
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_host_info",
        operation=lambda: service.host_info(name),
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        inputs={"name": name},
        source="govc",
    )


@router.get("/datastore-info")
async def datastore_info(
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_datastore_info",
        operation=service.datastore_info,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        source="govc",
    )


@router.get("/events")
async def events(
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_events",
        operation=service.events,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        source="govc",
    )


@router.get("/volume-ls")
async def volume_ls(
    refresh: bool = Query(default=False),
    service: GovcService = Depends(govc_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="govc_volume_ls",
        operation=service.volume_ls,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        source="govc",
    )
