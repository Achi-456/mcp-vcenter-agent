from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep, cache_dep, policy_dep, tool_registry_dep, vcenter_inventory_dep
from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService
from app.services.vcenter_inventory_service import VCenterInventoryService

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("/vm-details")
async def vm_details(
    name: str = Query(min_length=1),
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_vm_details",
        operation=lambda: service.get_vm_details(name),
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        inputs={"name": name},
    )


@router.get("/host-details")
async def host_details(
    name: str = Query(min_length=1),
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_host_details",
        operation=lambda: service.get_host_details(name),
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
        inputs={"name": name},
    )


@router.get("/datastore-health")
async def datastore_health(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_datastore_health",
        operation=service.get_datastore_health,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )


@router.get("/environment")
async def environment(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_environment_overview",
        operation=service.get_environment_overview,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )


@router.get("/rke2-vms")
async def rke2_vms(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="get_rke2_vms",
        operation=service.get_rke2_vms,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )
