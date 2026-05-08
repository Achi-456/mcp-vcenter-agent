from __future__ import annotations

import structlog

from app.tools.http_client import call_backend_get
from app.tools.schemas import RiskLevel, ToolCategory, ToolSpec

logger = structlog.get_logger()

# ── Tool definitions ────────────────────────────────────────────────────────

LIST_VMS_SPEC = ToolSpec(
    name="list_vms",
    display_name="List VMs",
    description="List all virtual machines with name, power state, CPU, memory, OS, IP, host, and tools status.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/inventory/vms",
    input_schema={
        "type": "object",
        "properties": {
            "refresh": {"type": "boolean", "description": "Bypass cache and force fresh data"},
        },
    },
)

GET_VM_DETAILS_SPEC = ToolSpec(
    name="get_vm_details",
    display_name="VM Details",
    description="Get detailed information for a specific VM: name, power state, host, datastore, IP, guest OS, CPU, memory, VMware Tools status.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/vm-details",
    input_schema={
        "type": "object",
        "properties": {
            "vm_name": {"type": "string", "description": "Name of the VM"},
            "refresh": {"type": "boolean", "description": "Bypass cache and force fresh data"},
        },
        "required": ["vm_name"],
    },
)

LIST_HOSTS_SPEC = ToolSpec(
    name="list_hosts",
    display_name="List Hosts",
    description="List all ESXi hosts with connection state, CPU cores, memory, VM count, vendor, model, and version.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
    backend_endpoint="/api/v1/inventory/hosts",
    input_schema={
        "type": "object",
        "properties": {
            "refresh": {"type": "boolean", "description": "Bypass cache and force fresh data"},
        },
    },
)

LIST_DATASTORES_SPEC = ToolSpec(
    name="list_datastores",
    display_name="List Datastores",
    description="List all datastores with capacity, free space, used percent, type, and accessibility.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
    backend_endpoint="/api/v1/inventory/datastores",
    input_schema={
        "type": "object",
        "properties": {
            "refresh": {"type": "boolean", "description": "Bypass cache and force fresh data"},
        },
    },
)

# ── Non-read-only stubs (blocked in this phase) ─────────────────────────────

GET_HOST_DETAILS_SPEC = ToolSpec(
    name="get_host_details",
    display_name="Host Details",
    description="Get detailed info for a specific ESXi host: VMs running, CPU/memory usage, maintenance mode status.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/host-details",
    input_schema={
        "type": "object",
        "properties": {
            "host_name": {"type": "string", "description": "Name of the ESXi host"},
            "refresh": {"type": "boolean"},
        },
        "required": ["host_name"],
    },
)

LIST_NETWORKS_SPEC = ToolSpec(
    name="list_networks",
    display_name="List Networks",
    description="List all networks and port groups with type and accessibility.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
    backend_endpoint="/api/v1/inventory/networks",
)

LIST_CLUSTERS_SPEC = ToolSpec(
    name="list_clusters",
    display_name="List Clusters",
    description="List all vSphere clusters with host count, VM count, DRS/HA status, total CPU, and memory.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
    backend_endpoint="/api/v1/inventory/clusters",
)

GET_ENVIRONMENT_OVERVIEW_SPEC = ToolSpec(
    name="get_environment_overview",
    display_name="Environment Overview",
    description="Get a complete vCenter environment overview: total VMs, powered on/off, hosts, datastore usage, networks, and alarm counts.",
    category=ToolCategory.CONTEXT,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=15,
    backend_endpoint="/api/v1/context/environment",
)

GET_POWERED_OFF_VMS_SPEC = ToolSpec(
    name="get_powered_off_vms",
    display_name="Powered-off VMs",
    description="List all virtual machines that are currently powered off.",
    category=ToolCategory.CONTEXT,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/powered-off-vms",
)

GET_DATASTORE_HEALTH_SPEC = ToolSpec(
    name="get_datastore_health",
    display_name="Datastore Health",
    description="Analyze datastore health: healthy, warning (70-85%), and critical (>85%) breakdown.",
    category=ToolCategory.CONTEXT,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
    backend_endpoint="/api/v1/context/datastore-health",
)

GET_ACTIVE_ALARMS_SPEC = ToolSpec(
    name="get_active_alarms",
    display_name="Active Alarms",
    description="Get all triggered/active vCenter alarms with severity, entity, and time.",
    category=ToolCategory.MONITORING,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/active-alarms",
)

GET_RECENT_EVENTS_SPEC = ToolSpec(
    name="get_recent_events",
    display_name="Recent Events",
    description="Fetch recent vCenter events (tasks, errors, warnings) with user and timestamp.",
    category=ToolCategory.MONITORING,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/recent-events",
)

GET_RKE2_VMS_SPEC = ToolSpec(
    name="get_rke2_vms",
    display_name="RKE2 Cluster VMs",
    description="Find all VMs related to the RKE2 Kubernetes cluster (agentic, cp, worker, db, utility nodes).",
    category=ToolCategory.CONTEXT,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/rke2-vms",
)

SEARCH_INVENTORY_SPEC = ToolSpec(
    name="search_inventory_object",
    display_name="Search Inventory Object",
    description="Search VMs, hosts, datastores, networks, and clusters by name. Returns typed matches with confidence scores.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=15,
    backend_endpoint="/api/v1/context/search",
    input_schema={
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "Search query"},
            "refresh": {"type": "boolean"},
        },
        "required": ["q"],
    },
)

LIST_AVAILABLE_TOOLS_SPEC = ToolSpec(
    name="list_available_tools",
    display_name="List Available Tools",
    description="List all tools available to the agent, grouped by category with status indicators.",
    category=ToolCategory.GENERAL,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    cache_ttl_seconds=60,
)

POWER_ON_VM_SPEC = ToolSpec(
    name="power_on_vm",
    display_name="Power On VM",
    description="Power on a virtual machine.",
    category=ToolCategory.VM_MANAGEMENT,
    risk_level=RiskLevel.APPROVAL_REQUIRED,
    enabled=False,
    implemented=False,
    requires_approval=True,
    backend_endpoint=None,
    input_schema={
        "type": "object",
        "properties": {"vm_name": {"type": "string", "description": "Name of the VM to power on"}},
        "required": ["vm_name"],
    },
)

POWER_OFF_VM_SPEC = ToolSpec(
    name="power_off_vm",
    display_name="Power Off VM",
    description="Power off a virtual machine.",
    category=ToolCategory.VM_MANAGEMENT,
    risk_level=RiskLevel.APPROVAL_REQUIRED,
    enabled=False,
    implemented=False,
    requires_approval=True,
    backend_endpoint=None,
    input_schema={
        "type": "object",
        "properties": {"vm_name": {"type": "string", "description": "Name of the VM to power off"}},
        "required": ["vm_name"],
    },
)


# ── Tool executors ──────────────────────────────────────────────────────────


async def _execute_list_tools(spec: ToolSpec, args: dict) -> dict:
    from app.tools.mcp_client import get_formatted_tool_list
    formatted = await get_formatted_tool_list()
    return {"ok": True, "tool": spec.name, "data": {"formatted": formatted}}


async def _execute_inventory_tool(spec: ToolSpec, args: dict) -> dict:
    refresh = args.pop("refresh", False)
    params = {}
    if spec.name == "get_vm_details":
        vm_name = args.get("vm_name", args.get("name", ""))
        if not vm_name:
            return {"ok": False, "error_code": "MISSING_PARAMETER", "message": "vm_name is required.", "tool": spec.name}
        params["name"] = vm_name
    if refresh:
        params["refresh"] = "true"

    result = await call_backend_get(spec.backend_endpoint, params=params)
    if not result.get("ok"):
        data = result.get("data", {})
        return {
            "ok": False,
            "tool": spec.name,
            "error_code": data.get("error_code", "BACKEND_ERROR"),
            "message": data.get("message", "Backend request failed"),
        }

    data = result.get("data", {})

    if spec.name == "list_vms":
        items = data.get("vms", data.get("items", []))
        return {"ok": True, "tool": spec.name, "count": len(items), "items": items}

    if spec.name == "list_hosts":
        items = data.get("hosts", data.get("items", []))
        return {"ok": True, "tool": spec.name, "count": len(items), "items": items}

    if spec.name == "list_datastores":
        items = data.get("datastores", data.get("items", []))
        return {"ok": True, "tool": spec.name, "count": len(items), "items": items}

    if spec.name == "get_vm_details":
        vms = data.get("vms", [])
        if vms:
            return {"ok": True, "tool": spec.name, "data": vms[0]}
        if "ok" in data and data.get("ok") is False:
            return {
                "ok": False,
                "tool": spec.name,
                "error_code": data.get("error_code", "VM_NOT_FOUND"),
                "message": data.get("message", "VM not found"),
            }
        vm = {k: v for k, v in data.items() if k not in ("source", "cached", "collected_at")}
        if vm and "power_state" in vm:
            return {"ok": True, "tool": spec.name, "data": vm}
        return {"ok": False, "tool": spec.name, "error_code": "VM_NOT_FOUND", "message": "VM not found in the response."}

    return {"ok": True, "tool": spec.name, "data": data}


# ── Executor mapping ────────────────────────────────────────────────────────


def get_executor(spec: ToolSpec):
    if spec.name == "list_available_tools":
        return _execute_list_tools
    inventory_tools = {
        "list_vms", "get_vm_details", "list_hosts", "list_datastores",
        "get_host_details", "list_networks", "list_clusters",
        "get_environment_overview", "get_powered_off_vms",
        "get_datastore_health", "get_active_alarms", "get_recent_events",
        "get_rke2_vms", "search_inventory_object",
    }
    if spec.name in inventory_tools:
        return _execute_inventory_tool
    return None


# ── All specs ───────────────────────────────────────────────────────────────


def get_all_tool_specs() -> list[ToolSpec]:
    return [
        LIST_VMS_SPEC,
        GET_VM_DETAILS_SPEC,
        LIST_HOSTS_SPEC,
        LIST_DATASTORES_SPEC,
        GET_HOST_DETAILS_SPEC,
        LIST_NETWORKS_SPEC,
        LIST_CLUSTERS_SPEC,
        GET_ENVIRONMENT_OVERVIEW_SPEC,
        GET_POWERED_OFF_VMS_SPEC,
        GET_DATASTORE_HEALTH_SPEC,
        GET_ACTIVE_ALARMS_SPEC,
        GET_RECENT_EVENTS_SPEC,
        GET_RKE2_VMS_SPEC,
        SEARCH_INVENTORY_SPEC,
        LIST_AVAILABLE_TOOLS_SPEC,
        POWER_ON_VM_SPEC,
        POWER_OFF_VM_SPEC,
    ]
