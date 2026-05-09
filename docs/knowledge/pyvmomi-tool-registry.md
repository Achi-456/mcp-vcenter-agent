# vCenter pyVmomi Tool Registry

This document defines the vCenter tool catalog for the vCenter Agentic Ops
Platform. Tools are grouped by category and risk level so the agent can decide
what may run automatically and what must be blocked or routed through approval.

## Risk Levels

| Risk | Meaning | Current behavior |
| --- | --- | --- |
| `read_only` | Queries state only | Can run automatically |
| `approval_required` | Changes state but is normally reversible or controlled | Visible but disabled until approval workflow exists |
| `destructive` | Can cause outage, data loss, or irreversible change | Visible but disabled until safety gates exist |

## 1. Connection And Session Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `connect_vcenter` | Connect or reconnect to vCenter using saved credentials | `read_only` |
| `disconnect_vcenter` | Disconnect current vCenter session | `read_only` |
| `check_vcenter_session` | Check if current pyVmomi session is alive | `read_only` |
| `get_vcenter_info` | Get vCenter name, version, build, and API type | `read_only` |
| `get_vcenter_health` | Check basic vCenter connectivity and session status | `read_only` |

Recommended first tools:

```text
connect_vcenter
check_vcenter_session
get_vcenter_info
```

## 2. Inventory Discovery Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `list_datacenters` | List vCenter datacenters | `read_only` |
| `list_clusters` | List compute clusters | `read_only` |
| `list_hosts` | List ESXi hosts | `read_only` |
| `list_vms` | List virtual machines | `read_only` |
| `list_datastores` | List datastores | `read_only` |
| `list_networks` | List networks and port groups | `read_only` |
| `list_resource_pools` | List resource pools | `read_only` |
| `list_folders` | List VM, host, and datastore folders | `read_only` |
| `search_inventory_object` | Search VMs, hosts, datastores, networks, and clusters by name | `read_only` |

These are safe for automatic execution.

## 3. VM Information Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `get_vm_details` | Get VM power state, CPU, memory, OS, IP, host, datastore, and VMware Tools status | `read_only` |
| `get_vm_power_state` | Get only VM power state | `read_only` |
| `get_vm_guest_info` | Get guest OS, IP address, and VMware Tools status | `read_only` |
| `get_vm_hardware` | Get vCPU, RAM, disks, and NICs | `read_only` |
| `get_vm_datastores` | Show datastores used by a VM | `read_only` |
| `get_vm_networks` | Show VM networks and port groups | `read_only` |
| `get_vm_host` | Show current ESXi host of a VM | `read_only` |
| `get_vm_path` | Show VM folder/path in inventory | `read_only` |
| `get_vm_moref` | Get VM Managed Object Reference ID | `read_only` |
| `find_vm_by_name` | Search VM by exact or partial name | `read_only` |
| `get_vms_by_power_state` | Filter VMs by `poweredOn`, `poweredOff`, or `suspended` | `read_only` |
| `get_powered_off_vms` | List powered-off VMs | `read_only` |
| `get_powered_on_vms` | List powered-on VMs | `read_only` |
| `get_vms_without_ip` | List VMs without guest IP | `read_only` |
| `get_vms_with_tools_not_running` | List VMs where VMware Tools is not running | `read_only` |

Important chatbot tools:

```text
get_vm_details
find_vm_by_name
get_powered_off_vms
get_vms_with_tools_not_running
```

## 4. VM Power Operation Tools

These must not run automatically in the current phase.

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `power_on_vm` | Power on a VM | `approval_required` |
| `power_off_vm` | Power off a VM | `approval_required` |
| `shutdown_guest` | Gracefully shut down guest OS | `approval_required` |
| `reboot_guest` | Gracefully reboot guest OS | `approval_required` |
| `reset_vm` | Hard reset VM | `destructive` |
| `suspend_vm` | Suspend VM | `approval_required` |
| `standby_guest` | Put guest OS into standby if supported | `approval_required` |

Recommended behavior: show these tools in the tool list, mark them as
approval-required or destructive, and block execution until the approval
workflow is implemented.

## 5. VM Creation, Clone, And Delete Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `create_vm` | Create a blank VM | `approval_required` |
| `clone_vm` | Clone an existing VM | `approval_required` |
| `clone_vm_from_template` | Deploy VM from template | `approval_required` |
| `rename_vm` | Rename VM | `approval_required` |
| `delete_vm` | Delete VM from inventory and/or disk | `destructive` |
| `destroy_vm` | Destroy VM object | `destructive` |
| `register_vm` | Register VM from `.vmx` file | `approval_required` |
| `unregister_vm` | Remove VM from inventory but keep files | `destructive` |
| `reconfigure_vm` | Change CPU, memory, disk, or NIC config | `approval_required` |

For now, list them but keep disabled.

## 6. VM Snapshot Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `list_snapshots` | List VM snapshots | `read_only` |
| `get_snapshot_tree` | Show snapshot tree | `read_only` |
| `create_snapshot` | Create VM snapshot | `approval_required` |
| `revert_to_snapshot` | Revert VM to snapshot | `destructive` |
| `delete_snapshot` | Delete one snapshot | `destructive` |
| `delete_all_snapshots` | Delete all snapshots | `destructive` |
| `find_old_snapshots` | Find snapshots older than N days | `read_only` |
| `find_large_snapshots` | Find large snapshot usage if available | `read_only` |

Safe now:

```text
list_snapshots
find_old_snapshots
```

Blocked now:

```text
create_snapshot
revert_to_snapshot
delete_snapshot
delete_all_snapshots
```

## 7. Host And ESXi Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `get_host_details` | Get ESXi host details | `read_only` |
| `list_host_vms` | List VMs running on a host | `read_only` |
| `get_host_hardware` | CPU, memory, vendor, and model | `read_only` |
| `get_host_version` | ESXi version/build | `read_only` |
| `get_host_networks` | Show host networking info | `read_only` |
| `get_host_datastores` | Show datastores mounted to host | `read_only` |
| `get_host_connection_state` | Connected, disconnected, or not responding | `read_only` |
| `get_hosts_in_maintenance` | List hosts in maintenance mode | `read_only` |
| `enter_maintenance_mode` | Put host into maintenance mode | `approval_required` |
| `exit_maintenance_mode` | Exit maintenance mode | `approval_required` |
| `reboot_host` | Reboot ESXi host | `destructive` |
| `shutdown_host` | Shut down ESXi host | `destructive` |
| `disconnect_host` | Disconnect host from vCenter | `destructive` |
| `reconnect_host` | Reconnect host to vCenter | `approval_required` |

Routing rule:

```text
"get details for esxi01.dclab.com" should route to get_host_details, not get_vm_details.
```

## 8. Cluster Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `list_clusters` | List clusters | `read_only` |
| `get_cluster_details` | Cluster CPU, memory, host count, and VM count | `read_only` |
| `get_cluster_hosts` | List hosts in cluster | `read_only` |
| `get_cluster_vms` | List VMs in cluster | `read_only` |
| `get_cluster_drs_status` | Check DRS enabled/status | `read_only` |
| `get_cluster_ha_status` | Check HA enabled/status | `read_only` |
| `get_cluster_resource_usage` | CPU/memory usage summary | `read_only` |
| `enable_ha` | Enable vSphere HA | `approval_required` |
| `disable_ha` | Disable vSphere HA | `destructive` |
| `enable_drs` | Enable DRS | `approval_required` |
| `disable_drs` | Disable DRS | `destructive` |

For the next implementation phase, only read-only cluster tools should run.

## 9. Datastore Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `list_datastores` | List datastores | `read_only` |
| `get_datastore_details` | Capacity, free space, type, and accessibility | `read_only` |
| `get_datastore_health` | Detect usage warning/critical | `read_only` |
| `get_datastore_vms` | List VMs using datastore | `read_only` |
| `get_datastores_above_threshold` | Find datastores above 80/85/90 percent usage | `read_only` |
| `browse_datastore` | Browse datastore files/folders | `read_only` |
| `rename_datastore` | Rename datastore | `approval_required` |
| `delete_datastore_file` | Delete file from datastore | `destructive` |
| `unmount_datastore` | Unmount datastore | `destructive` |
| `mount_datastore` | Mount datastore | `approval_required` |

Safe and useful now:

```text
get_datastore_health
get_datastores_above_threshold
get_datastore_details
```

## 10. Network Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `list_networks` | List standard networks and port groups | `read_only` |
| `list_dv_switches` | List distributed virtual switches | `read_only` |
| `list_dv_portgroups` | List distributed port groups | `read_only` |
| `get_network_details` | Get network or port group details | `read_only` |
| `get_vm_network_adapters` | Show VM NICs and connected networks | `read_only` |
| `get_vms_on_network` | List VMs connected to a port group | `read_only` |
| `change_vm_network` | Move VM NIC to another network | `approval_required` |
| `connect_vm_nic` | Connect VM NIC | `approval_required` |
| `disconnect_vm_nic` | Disconnect VM NIC | `approval_required` |
| `create_portgroup` | Create port group | `approval_required` |
| `delete_portgroup` | Delete port group | `destructive` |

Good read-only tools for the current agent:

```text
list_networks
get_vms_on_network
get_vm_network_adapters
```

## 11. Alarm And Event Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `get_active_alarms` | List active alarms | `read_only` |
| `get_alarm_details` | Get alarm details for object | `read_only` |
| `get_recent_events` | Get recent vCenter events | `read_only` |
| `get_events_for_vm` | Get recent events for a VM | `read_only` |
| `get_events_for_host` | Get recent events for an ESXi host | `read_only` |
| `get_events_by_user` | Filter events by username | `read_only` |
| `get_login_events` | Show recent vCenter login/logout events | `read_only` |
| `acknowledge_alarm` | Acknowledge alarm | `approval_required` |
| `reset_alarm_to_green` | Reset alarm status | `approval_required` |

Very useful for chat:

```text
get_active_alarms
get_recent_events
get_events_for_vm
get_events_for_host
```

## 12. Performance And Stats Tools

pyVmomi can use vCenter `PerformanceManager`.

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `get_vm_cpu_stats` | VM CPU usage | `read_only` |
| `get_vm_memory_stats` | VM memory usage | `read_only` |
| `get_vm_disk_stats` | VM disk latency/usage | `read_only` |
| `get_vm_network_stats` | VM network usage | `read_only` |
| `get_host_cpu_stats` | ESXi CPU usage | `read_only` |
| `get_host_memory_stats` | ESXi memory usage | `read_only` |
| `get_datastore_latency_stats` | Datastore latency metrics | `read_only` |
| `get_top_cpu_vms` | Top CPU-consuming VMs | `read_only` |
| `get_top_memory_vms` | Top memory-consuming VMs | `read_only` |
| `get_top_datastore_latency` | Highest datastore latency | `read_only` |

Good future tools:

```text
get_top_cpu_vms
get_top_memory_vms
get_vm_stats
get_host_stats
```

## 13. Search And Context Tools For AI Chat

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `get_environment_overview` | Summarize vCenter environment | `read_only` |
| `search_inventory_object` | Search object by name across inventory | `read_only` |
| `get_rke2_vms` | Detect RKE2-related VMs | `read_only` |
| `get_agentic_platform_vms` | Detect agentic platform VMs | `read_only` |
| `get_powered_off_vms` | List powered-off VMs | `read_only` |
| `get_critical_datastores` | Datastores above threshold | `read_only` |
| `get_unhealthy_objects` | Alarms, disconnected hosts, and critical datastores | `read_only` |
| `summarize_environment_health` | Combined health summary | `read_only` |

These are the best tools for natural language chat.

## 14. Reporting Tools

| Tool name | Purpose | Risk |
| --- | --- | --- |
| `emit_session_report` | Generate a report of what the agent did | `read_only` |
| `generate_inventory_report` | Create VM, host, and datastore report | `read_only` |
| `generate_health_report` | Create health summary report | `read_only` |
| `generate_alarm_report` | Create alarms report | `read_only` |
| `export_inventory_csv` | Export inventory table to CSV | `read_only` |
| `export_session_markdown` | Export chat/session as Markdown | `read_only` |

Good later tools:

```text
generate_health_report
emit_session_report
```

## Recommended Phase 1.4 Tool Set

Enable only these first:

```text
Connection:
- connect_vcenter
- check_vcenter_session
- get_vcenter_info

Inventory:
- get_environment_overview
- search_inventory_object
- list_vms
- get_vm_details
- list_hosts
- get_host_details
- list_clusters
- list_datastores
- get_datastore_details
- list_networks

Context:
- get_powered_off_vms
- get_powered_on_vms
- get_rke2_vms
- get_datastore_health
- get_active_alarms
- get_recent_events

Monitoring:
- get_events_for_vm
- get_events_for_host
```

Keep these visible but disabled:

```text
VM Power:
- power_on_vm
- power_off_vm
- reboot_guest
- reset_vm
- suspend_vm

Snapshots:
- create_snapshot
- revert_to_snapshot
- delete_snapshot
- delete_all_snapshots

Host:
- enter_maintenance_mode
- exit_maintenance_mode
- reboot_host
- shutdown_host

VM lifecycle:
- create_vm
- clone_vm
- delete_vm
- migrate_vm
```

## ToolSpec Format

Read-only example:

```json
{
  "name": "get_vm_details",
  "display_name": "Get VM Details",
  "description": "Get read-only details for a specific virtual machine.",
  "category": "Inventory & Information",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false,
  "phase": "1.4",
  "backend_endpoint": "/api/v1/context/vm-details",
  "args_schema": {
    "vm_name": "string"
  }
}
```

Risky tool example:

```json
{
  "name": "power_on_vm",
  "display_name": "Power On VM",
  "description": "Power on a virtual machine.",
  "category": "VM Management",
  "risk_level": "approval_required",
  "enabled": false,
  "implemented": false,
  "requires_approval": true,
  "phase": "future",
  "backend_endpoint": null
}
```

## Chatbot Answer For "list tools"

```text
I have access to these vCenter tools. In this phase, I can execute read-only
tools automatically. High-risk tools are visible but disabled until the approval
workflow is implemented.

Inventory & Information
- get_environment_overview - Available now
- list_vms - Available now
- get_vm_details - Available now
- list_hosts - Available now
- get_host_details - Available now
- list_datastores - Available now
- get_datastore_health - Available now
- list_networks - Available now
- search_inventory_object - Available now

Monitoring & Events
- get_active_alarms - Available now
- get_recent_events - Available now
- get_events_for_vm - Available now
- get_events_for_host - Available now

VM Management
- power_on_vm - Approval required, disabled in this phase
- power_off_vm - Approval required, disabled in this phase
- reboot_guest - Approval required, disabled in this phase
- reset_vm - Destructive, disabled in this phase
- delete_vm - Destructive, disabled in this phase

Snapshots
- list_snapshots - Available now
- create_snapshot - Approval required, disabled in this phase
- revert_to_snapshot - Destructive, disabled in this phase
- delete_snapshot - Destructive, disabled in this phase

Host Management
- get_host_details - Available now
- list_host_vms - Available now
- enter_maintenance_mode - Approval required, disabled in this phase
- reboot_host - Destructive, disabled in this phase
```

