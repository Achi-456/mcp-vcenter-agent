from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolDef:
    name: str
    display_name: str
    description: str
    category: str
    risk_level: str  # read_only | low_risk | approval_required | destructive
    enabled: bool = True
    implemented: bool = True
    requires_approval: bool = False
    phase: str = "1.4"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "risk_level": self.risk_level,
            "enabled": self.enabled,
            "implemented": self.implemented,
            "requires_approval": self.requires_approval,
            "phase": self.phase,
        }


# ── Complete Tool Registry ─────────────────────────────────────────────────

TOOLS: list[ToolDef] = [
    # ═══════════════════════════════════════════════════════════════════════
    # Inventory & Information (READ-ONLY — Phase 1.4 enabled)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="list_vms",
        display_name="List VMs",
        description="List all virtual machines with name, power state, CPU, memory, OS, IP, host, and tools status. Supports filtering by power state.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_vm_details",
        display_name="VM Details",
        description="Get detailed information for a specific VM: name, power state, host, datastore, IP address, guest OS, CPU, memory, VMware Tools status, disks, and network adapters.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_vm_stats",
        display_name="VM Performance Stats",
        description="Get real-time performance stats for a VM: CPU usage, memory usage, uptime, and consolidation status.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="list_hosts",
        display_name="List Hosts",
        description="List all ESXi hosts with connection state, power state, CPU cores, memory, VM count, vendor, model, and version.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_host_details",
        display_name="Host Details",
        description="Get detailed info for a specific ESXi host: VMs running, CPU/memory usage, maintenance mode status.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_vcenter_info",
        display_name="vCenter Info",
        description="Return high-level vCenter environment summary: version, build, total VMs, powered on/off counts, hosts, datastores, clusters.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="list_datastores",
        display_name="List Datastores",
        description="List all datastores with capacity, free space, used percent, type, and accessibility.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="list_networks",
        display_name="List Networks",
        description="List all networks and port groups with type and accessibility.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="list_clusters",
        display_name="List Clusters",
        description="List all vSphere clusters with host count, VM count, DRS/HA status, total CPU and memory.",
        category="Inventory & Information",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # VM Management (DANGEROUS — Phase 1.4 blocked)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="power_on_vm",
        display_name="Power On VM",
        description="Power on a virtual machine.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="power_off_vm",
        display_name="Power Off VM",
        description="Power off a virtual machine. Supports graceful shutdown (requires VMware Tools) or forced hard power off.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="reboot_guest",
        display_name="Reboot Guest",
        description="Graceful guest OS reboot (requires VMware Tools).",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="reset_vm",
        display_name="Reset VM",
        description="Hard reset a virtual machine.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="suspend_vm",
        display_name="Suspend VM",
        description="Suspend a virtual machine to disk.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="create_vm",
        display_name="Create VM",
        description="Create a new blank virtual machine with specified CPU, memory, and datastore.",
        category="VM Management",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="clone_vm",
        display_name="Clone VM",
        description="Clone an existing virtual machine.",
        category="VM Management",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="delete_vm",
        display_name="Delete VM",
        description="Delete a virtual machine from disk. VM must be powered off first.",
        category="VM Management",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="rename_vm",
        display_name="Rename VM",
        description="Rename an existing virtual machine.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="migrate_vm",
        display_name="Migrate VM",
        description="Migrate a running VM (vMotion) to a new host or datastore.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="change_vm_network",
        display_name="Change VM Network",
        description="Change the network configuration of the primary network adapter on a VM.",
        category="VM Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # VM Snapshots (DANGEROUS — Phase 1.4 blocked)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="list_snapshots",
        display_name="List Snapshots",
        description="List all snapshots for a specific VM.",
        category="VM Snapshots",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="create_snapshot",
        display_name="Create Snapshot",
        description="Create a snapshot of a VM with optional memory capture.",
        category="VM Snapshots",
        risk_level="low_risk",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="revert_to_snapshot",
        display_name="Revert to Snapshot",
        description="Revert a VM to a named snapshot, discarding current state.",
        category="VM Snapshots",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="delete_snapshot",
        display_name="Delete Snapshot",
        description="Delete a named snapshot from a VM.",
        category="VM Snapshots",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Host Management (DANGEROUS — Phase 1.4 blocked)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="enter_maintenance_mode",
        display_name="Enter Maintenance Mode",
        description="Put an ESXi host into maintenance mode, evacuating powered-off VMs.",
        category="Host Management",
        risk_level="destructive",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),
    ToolDef(
        name="exit_maintenance_mode",
        display_name="Exit Maintenance Mode",
        description="Take an ESXi host out of maintenance mode.",
        category="Host Management",
        risk_level="approval_required",
        enabled=False,
        implemented=False,
        requires_approval=True,
        phase="future",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Monitoring & Events (READ-ONLY — Phase 1.4 enabled)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="get_active_alarms",
        display_name="Active Alarms",
        description="Get all triggered/active vCenter alarms with severity, entity, and time.",
        category="Monitoring & Events",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_recent_events",
        display_name="Recent Events",
        description="Fetch recent vCenter events (tasks, errors, warnings) with user and timestamp.",
        category="Monitoring & Events",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Context Helpers (READ-ONLY — Phase 1.4 enabled)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="get_environment_overview",
        display_name="Environment Overview",
        description="Get a complete vCenter environment overview: total VMs, powered on/off, hosts, datastore usage, networks, and alarm counts.",
        category="Context Helpers",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_powered_off_vms",
        display_name="Powered-off VMs",
        description="List all virtual machines that are currently powered off.",
        category="Context Helpers",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_datastore_health",
        display_name="Datastore Health",
        description="Analyze datastore health: healthy, warning (70-85%), and critical (>85%) breakdown.",
        category="Context Helpers",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="get_rke2_vms",
        display_name="RKE2 Cluster VMs",
        description="Find all VMs related to the RKE2 Kubernetes cluster (agentic, cp, worker, db, utility nodes).",
        category="Context Helpers",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # General & Utility (READ-ONLY — Phase 1.4 enabled)
    # ═══════════════════════════════════════════════════════════════════════
    ToolDef(
        name="list_available_tools",
        display_name="List Available Tools",
        description="List all tools available to the agent, grouped by category with status indicators (available, approval required, disabled).",
        category="General & Utility",
        risk_level="read_only",
        enabled=True,
        implemented=True,
    ),
    ToolDef(
        name="govc_command_readonly",
        display_name="Govc Read-Only Command",
        description="Run a restricted read-only govc CLI command for VMware inspection. Destructive subcommands are blocked.",
        category="General & Utility",
        risk_level="read_only",
        enabled=False,
        implemented=False,
        phase="1.5",
    ),
    ToolDef(
        name="web_search",
        display_name="Web Search",
        description="Search the public web for VMware documentation, KB articles, and best practices.",
        category="General & Utility",
        risk_level="read_only",
        enabled=False,
        implemented=False,
        phase="1.5",
    ),
]

# ── Lookup helpers ──────────────────────────────────────────────────────────

def get_tool(name: str) -> ToolDef | None:
    for t in TOOLS:
        if t.name == name:
            return t
    return None


def get_enabled_tools() -> list[ToolDef]:
    return [t for t in TOOLS if t.enabled and t.implemented]


def get_tools_by_category(category: str) -> list[ToolDef]:
    return [t for t in TOOLS if t.category == category]


def get_categories() -> list[str]:
    seen = []
    for t in TOOLS:
        if t.category not in seen:
            seen.append(t.category)
    return seen


def format_tool_list() -> str:
    """Rich grouped Markdown for 'list tools' assistant response."""
    categories = get_categories()
    lines = [
        "Of course. I have access to these tools for the vCenter environment:\n",
    ]
    for cat in categories:
        tools = get_tools_by_category(cat)
        lines.append(f"## {cat}\n")
        for t in tools:
            status = ""
            if t.enabled and t.implemented:
                status = "Available now"
            elif t.risk_level == "read_only" and t.phase != "1.4":
                status = "Planned"
            elif t.requires_approval:
                status = "Approval required / disabled in Phase 1.4"
            else:
                status = "Disabled in this phase"
            lines.append(f"- **{t.name}** — {t.description}  ")
            lines.append(f"  *{status}*  \n")
    lines.append("---")
    lines.append("Only read-only tools are currently executable. Destructive operations require future phase approval gates.")
    return "\n".join(lines)
