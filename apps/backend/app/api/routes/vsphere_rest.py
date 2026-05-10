from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep, cache_dep, policy_dep, tool_registry_dep, vsphere_rest_dep
from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService
from app.services.vsphere_rest_service import VSphereRestService

router = APIRouter(prefix="/api/v1/vsphere-rest", tags=["vsphere-rest"])


@router.get("/about")
async def about(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_about", operation=service.about, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")


@router.get("/appliance/health")
async def appliance_health(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_appliance_health", operation=service.appliance_health, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")


@router.get("/tag-categories")
async def tag_categories(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_tag_categories", operation=service.list_tag_categories, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")


@router.get("/tags")
async def tags(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_tags", operation=service.list_tags, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")


@router.get("/tags/attached")
async def attached_tags(object_id: str = Query(min_length=1), refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_attached_tags", operation=lambda: service.list_attached_tags(object_id), registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, inputs={"object_id": object_id}, source="vsphere_rest")


@router.get("/content-libraries")
async def content_libraries(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_content_libraries", operation=service.list_content_libraries, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")


@router.get("/content-libraries/{library_id}/items")
async def library_items(library_id: str, refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_library_items", operation=lambda: service.list_library_items(library_id), registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, inputs={"library_id": library_id}, source="vsphere_rest")


@router.get("/tasks/recent")
async def recent_tasks(refresh: bool = Query(default=False), service: VSphereRestService = Depends(vsphere_rest_dep), registry: ToolRegistryService = Depends(tool_registry_dep), policy: PolicyService = Depends(policy_dep), cache: CacheService = Depends(cache_dep), audit: AuditService = Depends(audit_dep)):
    return await run_vcenter_tool(tool_name="vsphere_rest_list_recent_tasks", operation=service.list_recent_tasks, registry=registry, policy=policy, cache=cache, audit=audit, refresh=refresh, source="vsphere_rest")
