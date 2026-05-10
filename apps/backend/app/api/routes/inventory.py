from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep, cache_dep, policy_dep, tool_registry_dep, vcenter_inventory_dep
from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService
from app.services.vcenter_inventory_service import VCenterInventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/overview")
async def overview(
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


@router.get("/vms")
async def vms(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="list_vms",
        operation=service.list_vms,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )


@router.get("/hosts")
async def hosts(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="list_hosts",
        operation=service.list_hosts,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )


@router.get("/datastores")
async def datastores(
    refresh: bool = Query(default=False),
    service: VCenterInventoryService = Depends(vcenter_inventory_dep),
    registry: ToolRegistryService = Depends(tool_registry_dep),
    policy: PolicyService = Depends(policy_dep),
    cache: CacheService = Depends(cache_dep),
    audit: AuditService = Depends(audit_dep),
):
    return await run_vcenter_tool(
        tool_name="list_datastores",
        operation=service.list_datastores,
        registry=registry,
        policy=policy,
        cache=cache,
        audit=audit,
        refresh=refresh,
    )
