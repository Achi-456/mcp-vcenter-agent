# pyVmomi Tools — Primary vCenter Integration Layer

## Purpose

`pyVmomi` is the primary Python SDK layer for the AgenticOps FastAPI backend.

Recommended flow:

```text
Agent Engine → FastAPI Backend → pyVmomi VCenterSession → vCenter SOAP/VIM API
```

Use pyVmomi for structured, production-grade read-only inventory and monitoring operations.

---

## 1. Connection / Session Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `connect_vcenter` | Force reconnect to vCenter | read_only | implemented |
| `check_vcenter_session` | Check if current session is alive | read_only | implemented/planned |
| `get_vcenter_info` | vCenter version/build/about info | read_only | planned |
| `disconnect_vcenter` | Disconnect current session | read_only | optional |

---

## 2. Inventory Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_environment_overview` | Full environment summary | read_only | implemented |
| `search_inventory_object` | Search VM/host/datastore/network/cluster | read_only | planned |
| `list_datacenters` | List datacenters | read_only | planned |
| `list_clusters` | List clusters | read_only | implemented |
| `list_hosts` | List ESXi hosts | read_only | implemented |
| `list_vms` | List virtual machines | read_only | implemented |
| `list_datastores` | List datastores | read_only | implemented |
| `list_networks` | List networks / port groups | read_only | implemented |
| `list_resource_pools` | List resource pools | read_only | planned |
| `list_folders` | List inventory folders | read_only | planned |

---

## 3. VM Details Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_vm_details` | VM power, CPU, memory, IP, host, datastore, tools | read_only | implemented/fixing |
| `find_vm_by_name` | Exact/partial VM search | read_only | planned |
| `get_vm_power_state` | VM power state only | read_only | planned |
| `get_vm_guest_info` | Guest OS, IP, VMware Tools | read_only | planned |
| `get_vm_hardware` | CPU, RAM, disks, NICs | read_only | planned |
| `get_vm_datastores` | Datastores used by VM | read_only | planned |
| `get_vm_networks` | Networks/portgroups used by VM | read_only | planned |
| `get_vm_host` | ESXi host for VM | read_only | planned |
| `get_vms_by_power_state` | Filter poweredOn/poweredOff/suspended | read_only | planned |
| `get_powered_off_vms` | Powered-off VM list | read_only | implemented |
| `get_powered_on_vms` | Powered-on VM list | read_only | implemented/planned |
| `get_vms_without_ip` | VMs with no guest IP | read_only | planned |
| `get_vms_with_tools_not_running` | VMware Tools not running/outdated | read_only | planned |

---

## 4. Host Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_host_details` | ESXi host version, build, CPU, memory, cluster | read_only | implemented/fixing |
| `list_host_vms` | VMs running on host | read_only | planned |
| `get_host_hardware` | Vendor/model/CPU/memory | read_only | planned |
| `get_host_version` | ESXi version/build | read_only | planned |
| `get_host_datastores` | Datastores mounted to host | read_only | planned |
| `get_host_networks` | Host network summary | read_only | planned |
| `get_host_connection_state` | connected/disconnected/notResponding | read_only | planned |
| `get_hosts_in_maintenance` | Hosts currently in maintenance | read_only | planned |

### Disabled until approval workflow

| Tool | Purpose | Risk |
|---|---|---:|
| `enter_maintenance_mode` | Put host in maintenance mode | approval_required |
| `exit_maintenance_mode` | Exit maintenance mode | approval_required |
| `reboot_host` | Reboot host | destructive |
| `shutdown_host` | Shut down host | destructive |
| `disconnect_host` | Disconnect host from vCenter | destructive |

---

## 5. Datastore Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_datastore_details` | Capacity/free/type/accessibility | read_only | planned |
| `get_datastore_health` | Usage threshold warning/critical | read_only | implemented |
| `get_datastores_above_threshold` | Datastores above N percent | read_only | planned |
| `get_datastore_vms` | VMs using datastore | read_only | planned |
| `browse_datastore_readonly` | Browse datastore files read-only | read_only | future |

### Disabled

| Tool | Purpose | Risk |
|---|---|---:|
| `rename_datastore` | Rename datastore | approval_required |
| `delete_datastore_file` | Delete datastore file | destructive |
| `unmount_datastore` | Unmount datastore | destructive |
| `mount_datastore` | Mount datastore | approval_required |

---

## 6. Network Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_network_details` | Network/portgroup detail | read_only | planned |
| `list_dv_switches` | Distributed switches | read_only | planned |
| `list_dv_portgroups` | Distributed portgroups | read_only | planned |
| `get_vms_on_network` | VMs connected to network | read_only | planned |
| `get_vm_network_adapters` | NICs for VM | read_only | planned |

### Disabled

| Tool | Purpose | Risk |
|---|---|---:|
| `change_vm_network` | Change VM network adapter | approval_required |
| `connect_vm_nic` | Connect VM NIC | approval_required |
| `disconnect_vm_nic` | Disconnect VM NIC | approval_required |
| `create_portgroup` | Create portgroup | approval_required |
| `delete_portgroup` | Delete portgroup | destructive |

---

## 7. Alarm / Events Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_active_alarms` | Active alarms | read_only | implemented |
| `get_alarm_details` | Alarm detail for object | read_only | planned |
| `get_recent_events` | Recent events | read_only | implemented |
| `get_events_for_vm` | Events for VM | read_only | planned |
| `get_events_for_host` | Events for host | read_only | planned |
| `get_storage_related_events` | Storage/datastore/CNS events | read_only | planned |
| `get_login_events` | Login/logout events | read_only | planned |

---

## 8. Snapshot Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `list_snapshots` | List VM snapshots | read_only | planned |
| `get_snapshot_tree` | Snapshot tree | read_only | planned |
| `find_old_snapshots` | Snapshots older than N days | read_only | planned |
| `find_large_snapshots` | Large snapshots if size data available | read_only | planned |

### Disabled

| Tool | Purpose | Risk |
|---|---|---:|
| `create_snapshot` | Create snapshot | approval_required |
| `revert_to_snapshot` | Revert VM | destructive |
| `delete_snapshot` | Delete snapshot | destructive |
| `delete_all_snapshots` | Delete all snapshots | destructive |

---

## 9. Performance Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_vm_stats` | VM CPU/memory/disk/network stats | read_only | future |
| `get_host_stats` | Host CPU/memory/network stats | read_only | future |
| `get_top_cpu_vms` | Highest CPU usage VMs | read_only | future |
| `get_top_memory_vms` | Highest memory usage VMs | read_only | future |
| `get_datastore_latency_stats` | Datastore latency | read_only | future |

---

## 10. Context / AI Tools

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `get_rke2_vms` | Detect RKE2-related VMs | read_only | implemented |
| `get_agentic_platform_vms` | Detect AgenticOps platform VMs | read_only | planned |
| `get_unhealthy_objects` | Alarms + critical datastores + disconnected hosts | read_only | planned |
| `summarize_environment_health` | Combined health report | read_only | planned |
| `emit_session_report` | Report of tools/actions taken | read_only | planned |

---

## Recommended pyVmomi enablement

```text
Enable now:
- get_environment_overview
- list_vms
- get_vm_details
- list_hosts
- get_host_details
- list_clusters
- list_datastores
- get_datastore_health
- list_networks
- get_active_alarms
- get_recent_events
- get_rke2_vms

Add next:
- search_inventory_object
- list_snapshots
- get_events_for_vm
- get_events_for_host
- get_datastore_details
- get_vms_with_tools_not_running
```
