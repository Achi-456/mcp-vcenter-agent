# govmomi Tools — Go SDK / CNS / Deep vSphere Integration

## Purpose

`govmomi` is best used when the platform needs a Go-based vSphere integration service or MCP server for deeper vSphere automation, especially around CNS / CSI / volume operations.

Recommended integration style:

```text
Agent Engine → MCP Tool Router → mcp-vcenter-govmomi → govmomi Go SDK → vCenter / CNS / PBM / VSLM APIs
```

## When to use govmomi

```text
- CNS volume query and mapping
- vSphere CSI investigation
- high-performance vSphere API operations
- Go-based MCP server
- advanced vSphere automation
- fallback where pyVmomi is limited
```

---

## 1. Connection / Session Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_connect_vcenter` | Connect to vCenter through govmomi client | read_only | future |
| `govmomi_check_session` | Validate vCenter session | read_only | future |
| `govmomi_get_about` | Get vCenter version/build/API info | read_only | future |
| `govmomi_disconnect` | Close govmomi session | read_only | future |

---

## 2. Inventory Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_list_datacenters` | List datacenters | read_only | future |
| `govmomi_list_clusters` | List clusters | read_only | future |
| `govmomi_list_hosts` | List ESXi hosts | read_only | future |
| `govmomi_list_vms` | List VMs | read_only | future |
| `govmomi_list_datastores` | List datastores | read_only | future |
| `govmomi_list_networks` | List networks / port groups | read_only | future |
| `govmomi_search_inventory` | Search object by name/MoRef/path | read_only | future |

---

## 3. VM Read-Only Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_get_vm_details` | VM power, host, datastore, guest, network info | read_only | future |
| `govmomi_get_vm_host` | Current ESXi host for VM | read_only | future |
| `govmomi_get_vm_datastores` | Datastores used by VM | read_only | future |
| `govmomi_get_vm_networks` | VM NIC/portgroup info | read_only | future |
| `govmomi_get_vm_snapshots` | Snapshot tree | read_only | future |
| `govmomi_get_vm_events` | Recent VM events | read_only | future |

---

## 4. Host Read-Only Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_get_host_details` | ESXi version, build, model, CPU, memory | read_only | future |
| `govmomi_list_host_vms` | VMs running on host | read_only | future |
| `govmomi_get_host_datastores` | Datastores mounted to host | read_only | future |
| `govmomi_get_host_networks` | Host networking summary | read_only | future |
| `govmomi_get_host_events` | Recent host events | read_only | future |

---

## 5. Datastore Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_get_datastore_details` | Capacity, free, type, accessible | read_only | future |
| `govmomi_get_datastore_health` | Usage threshold classification | read_only | future |
| `govmomi_list_datastore_vms` | VMs using datastore | read_only | future |
| `govmomi_browse_datastore` | Read-only datastore browser | read_only | future |

---

## 6. CNS / CSI Tools

Strongest reason to add govmomi.

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_list_cns_volumes` | Query CNS volumes | read_only | Fix 8/9 |
| `govmomi_get_cns_volume_details` | CNS volume details by volume ID | read_only | Fix 8/9 |
| `govmomi_map_pv_to_cns_volume` | Map Kubernetes PV volumeHandle to CNS volume | read_only | Fix 8/9 |
| `govmomi_map_cns_volume_to_datastore` | Find backing datastore for CNS volume | read_only | Fix 8/9 |
| `govmomi_check_cns_volume_health` | CNS volume health summary | read_only | Fix 8/9 |
| `govmomi_list_orphan_cns_volumes` | Find CNS volumes without matching PV | read_only | future |
| `govmomi_list_stale_cns_volumes` | Find stale CNS volumes | read_only | future |

### Blocked until approval workflow

| Tool | Purpose | Risk |
|---|---|---:|
| `govmomi_delete_cns_volume` | Delete CNS volume | destructive |
| `govmomi_extend_cns_volume` | Extend CNS volume | approval_required |
| `govmomi_create_cns_volume` | Create CNS volume | approval_required |

---

## 7. PBM / Storage Policy Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_list_storage_policies` | List vSphere storage policies | read_only | future |
| `govmomi_get_storage_policy_details` | Policy rules/capabilities | read_only | future |
| `govmomi_validate_storage_policy_mapping` | Check StorageClass to vSphere policy mapping | read_only | future |
| `govmomi_check_datastore_policy_compatibility` | Check datastore compatibility with policy | read_only | future |

---

## 8. Monitoring / Events Tools

| Tool | Purpose | Risk | Phase |
|---|---|---:|---|
| `govmomi_get_recent_events` | vCenter recent events | read_only | future |
| `govmomi_get_storage_events` | Storage/CNS/datastore events | read_only | future |
| `govmomi_get_active_alarms` | Triggered alarms | read_only | future |
| `govmomi_get_object_alarms` | Alarms for VM/host/datastore | read_only | future |

---

## 9. Approval-Required Automation Tools

Do not enable these in current phase.

| Tool | Purpose | Risk | Status |
|---|---|---:|---|
| `govmomi_power_on_vm` | Power on VM | approval_required | disabled |
| `govmomi_power_off_vm` | Power off VM | approval_required | disabled |
| `govmomi_create_snapshot` | Create snapshot | approval_required | disabled |
| `govmomi_delete_snapshot` | Delete snapshot | destructive | disabled |
| `govmomi_migrate_vm` | vMotion / Storage vMotion | approval_required | disabled |
| `govmomi_enter_maintenance_mode` | Host maintenance mode | approval_required | disabled |
| `govmomi_delete_vm` | Delete VM | destructive | disabled |

---

## Recommended first implementation

```text
1. govmomi_list_cns_volumes
2. govmomi_get_cns_volume_details
3. govmomi_map_pv_to_cns_volume
4. govmomi_map_cns_volume_to_datastore
5. govmomi_list_storage_policies
6. govmomi_validate_storage_policy_mapping
```

This will strongly improve the CSI VA Check workflow.
