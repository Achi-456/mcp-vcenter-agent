from app.core.errors import ErrorCode
from app.schemas.tools import RiskLevel, ToolSpec


def _tool(
    name: str,
    display_name: str,
    description: str,
    *,
    domain: str = "vcenter",
    category: str = "Inventory",
    agent: str = "vcenter_inventory_agent",
    backend: str = "pyvmomi",
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    enabled: bool = True,
    implemented: bool = False,
    requires_approval: bool = False,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        display_name=display_name,
        description=description,
        domain=domain,
        category=category,
        agent=agent,
        backend=backend,
        risk_level=risk_level,
        enabled=enabled,
        implemented=implemented,
        requires_approval=requires_approval,
        input_schema={},
        output_schema={},
    )


TOOLS: tuple[ToolSpec, ...] = (
    _tool("get_environment_overview", "Environment Overview", "Summarize vCenter environment health.", implemented=True),
    _tool("list_vms", "List VMs", "List virtual machines.", implemented=True),
    _tool("get_vm_details", "Get VM Details", "Get details for a specific virtual machine.", implemented=True),
    _tool("list_hosts", "List Hosts", "List ESXi hosts.", implemented=True),
    _tool("get_host_details", "Get Host Details", "Get details for a specific ESXi host.", implemented=True),
    _tool("list_datastores", "List Datastores", "List vCenter datastores.", implemented=True),
    _tool("get_datastore_health", "Datastore Health", "Check datastore usage and accessibility.", implemented=True),
    _tool("get_active_alarms", "Active Alarms", "List active vCenter alarms.", category="Monitoring", implemented=True),
    _tool("get_recent_events", "Recent Events", "List recent vCenter events.", category="Monitoring", implemented=True),
    _tool("get_rke2_vms", "RKE2 VMs", "Detect RKE2 and AgenticOps platform VMs.", category="Context", implemented=True),
    _tool("govc_about", "govc About", "Read vCenter about information through govc.", backend="govc", implemented=True),
    _tool("govc_vm_info", "govc VM Info", "Read VM info through govc.", backend="govc", implemented=True),
    _tool("govc_host_info", "govc Host Info", "Read host info through govc.", backend="govc", implemented=True),
    _tool("govc_datastore_info", "govc Datastore Info", "Read datastore info through govc.", backend="govc", implemented=True),
    _tool("govc_events", "govc Events", "Read recent vCenter events through govc.", backend="govc", category="Monitoring", implemented=True),
    _tool("govc_volume_ls", "govc Volume List", "Read govc volume list when supported.", backend="govc", category="Storage", implemented=True),
    _tool("vsphere_rest_about", "vSphere REST About", "Read vSphere appliance version through REST.", backend="vsphere_rest", implemented=True),
    _tool("vsphere_rest_appliance_health", "vSphere REST Appliance Health", "Read appliance health through REST.", backend="vsphere_rest", category="Monitoring", implemented=True),
    _tool("vsphere_rest_list_tag_categories", "vSphere REST Tag Categories", "List tag categories through REST.", backend="vsphere_rest", category="Tags", implemented=True),
    _tool("vsphere_rest_list_tags", "vSphere REST Tags", "List tags through REST.", backend="vsphere_rest", category="Tags", implemented=True),
    _tool("vsphere_rest_list_attached_tags", "vSphere REST Attached Tags", "List attached tags through REST.", backend="vsphere_rest", category="Tags", implemented=True),
    _tool("vsphere_rest_list_content_libraries", "vSphere REST Content Libraries", "List content libraries through REST.", backend="vsphere_rest", category="Content Library", implemented=True),
    _tool("vsphere_rest_list_library_items", "vSphere REST Library Items", "List content library items through REST.", backend="vsphere_rest", category="Content Library", implemented=True),
    _tool("vsphere_rest_list_recent_tasks", "vSphere REST Recent Tasks", "List recent tasks through REST.", backend="vsphere_rest", category="Monitoring", implemented=True),
    _tool(
        "get_csi_va_check",
        "CSI VA Check",
        "Read-only Kubernetes and vSphere CSI validation assessment.",
        domain="kubernetes",
        category="Kubernetes CSI / Storage Validation",
        agent="csi_validation_agent",
        backend="kubernetes+pyvmomi",
    ),
    _tool(
        "power_on_vm",
        "Power On VM",
        "Power on a virtual machine.",
        category="VM Management",
        risk_level=RiskLevel.APPROVAL_REQUIRED,
        enabled=False,
        requires_approval=True,
    ),
    _tool(
        "power_off_vm",
        "Power Off VM",
        "Power off a virtual machine.",
        category="VM Management",
        risk_level=RiskLevel.APPROVAL_REQUIRED,
        enabled=False,
        requires_approval=True,
    ),
    _tool(
        "delete_vm",
        "Delete VM",
        "Delete a virtual machine.",
        category="VM Lifecycle",
        risk_level=RiskLevel.DESTRUCTIVE,
        enabled=False,
        requires_approval=True,
    ),
    _tool(
        "enter_maintenance_mode",
        "Enter Maintenance Mode",
        "Put an ESXi host into maintenance mode.",
        category="Host Management",
        risk_level=RiskLevel.APPROVAL_REQUIRED,
        enabled=False,
        requires_approval=True,
    ),
    _tool(
        "delete_snapshot",
        "Delete Snapshot",
        "Delete a VM snapshot.",
        category="Snapshots",
        risk_level=RiskLevel.DESTRUCTIVE,
        enabled=False,
        requires_approval=True,
    ),
    _tool(
        "delete_cns_volume",
        "Delete CNS Volume",
        "Delete a vSphere CNS volume.",
        domain="vcenter",
        category="Storage",
        backend="govmomi",
        risk_level=RiskLevel.DESTRUCTIVE,
        enabled=False,
        requires_approval=True,
    ),
)


class ToolRegistryService:
    def __init__(self, tools: tuple[ToolSpec, ...] = TOOLS, extra_tools: list[ToolSpec] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools}
        for tool in extra_tools or []:
            self._tools[tool.name] = tool

    def list_tools(self, extra_tools: list[ToolSpec] | None = None) -> list[ToolSpec]:
        tools = dict(self._tools)
        for tool in extra_tools or []:
            tools[tool.name] = tool
        return sorted(tools.values(), key=lambda tool: tool.name)

    def get_tool(self, tool_name: str) -> ToolSpec:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(ErrorCode.TOOL_NOT_FOUND)
        return tool

    def categories(self) -> list[str]:
        return sorted({tool.category for tool in self._tools.values()})

    def agents(self) -> list[str]:
        return sorted({tool.agent for tool in self._tools.values()})
