import os
from dataclasses import dataclass, field

FASTAPI_INTERNAL = os.getenv(
    "FASTAPI_INTERNAL_URL",
    "http://fastapi.agentic-app.svc.cluster.local:8000",
)


@dataclass
class ToolDef:
    name: str
    description: str
    risk: str  # read_only | low_risk | approval_required | destructive
    category: str
    api_endpoint: str
    requires_approval: bool = False


TOOLS: list[ToolDef] = [
    ToolDef(
        name="get_environment_overview",
        description="Get a complete vCenter environment overview: VMs, hosts, datastores, networks, and alarms summary.",
        risk="read_only",
        category="context",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/environment",
    ),
    ToolDef(
        name="list_vms",
        description="List all virtual machines with name, power state, CPU, memory, OS, IP, host, and tools status.",
        risk="read_only",
        category="inventory",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/vms",
    ),
    ToolDef(
        name="list_hosts",
        description="List all ESXi hosts with connection state, CPU, memory, VM count, vendor, and version.",
        risk="read_only",
        category="inventory",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/hosts",
    ),
    ToolDef(
        name="list_clusters",
        description="List all vSphere clusters with host count, VM count, total CPU, and memory.",
        risk="read_only",
        category="inventory",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/clusters",
    ),
    ToolDef(
        name="list_datastores",
        description="List all datastores with capacity, free space, used percent, and accessibility.",
        risk="read_only",
        category="inventory",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/datastores",
    ),
    ToolDef(
        name="list_networks",
        description="List all networks and port groups with type and accessibility.",
        risk="read_only",
        category="inventory",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/inventory/networks",
    ),
    ToolDef(
        name="get_powered_off_vms",
        description="Get all virtual machines that are currently powered off.",
        risk="read_only",
        category="context",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/powered-off-vms",
    ),
    ToolDef(
        name="get_datastore_health",
        description="Analyze datastore health showing healthy, warning, and critical threshold breakdowns.",
        risk="read_only",
        category="context",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/datastore-health",
    ),
    ToolDef(
        name="get_active_alarms",
        description="List all active vCenter alarms sorted by severity (critical first).",
        risk="read_only",
        category="monitoring",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/active-alarms",
    ),
    ToolDef(
        name="get_recent_events",
        description="List recent vCenter events with error and warning counts.",
        risk="read_only",
        category="monitoring",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/recent-events",
    ),
    ToolDef(
        name="get_rke2_vms",
        description="Find all VMs related to the RKE2 Kubernetes cluster (agentic, cp, worker, db, utility nodes).",
        risk="read_only",
        category="context",
        api_endpoint=f"{FASTAPI_INTERNAL}/api/v1/context/rke2-vms",
    ),
]


def get_tool(name: str) -> ToolDef | None:
    for t in TOOLS:
        if t.name == name:
            return t
    return None


def get_tools_by_category(category: str) -> list[ToolDef]:
    return [t for t in TOOLS if t.category == category]


def get_all_tools() -> list[ToolDef]:
    return list(TOOLS)
