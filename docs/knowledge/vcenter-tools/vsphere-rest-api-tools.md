# vSphere REST API Tools — vCenter REST / Automation API Integration

## Purpose

vSphere REST API tools are useful where REST is cleaner than pyVmomi SOAP:

```text
- tagging
- categories
- content library
- appliance health
- vCenter system information
- session/login checks
- task summaries
```

Recommended flow:

```text
Agent Engine → Tool Registry → FastAPI vSphere REST service → vCenter REST / Automation API
```

Use REST beside pyVmomi, not as a full replacement.

---

## 1. Session / Authentication Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_create_session` | Create REST session | read_only |
| `vsphere_rest_check_session` | Verify REST session is active | read_only |
| `vsphere_rest_delete_session` | Logout REST session | read_only |

For backend use only. Do not expose session token to frontend or LLM.

---

## 2. vCenter System / Appliance Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_get_vcenter_info` | Basic vCenter info | read_only |
| `vsphere_rest_get_appliance_health` | Appliance health summary | read_only |
| `vsphere_rest_get_appliance_version` | Appliance version/build | read_only |
| `vsphere_rest_get_time` | vCenter time/NTP style check | read_only |
| `vsphere_rest_get_services` | vCenter services status if available | read_only |

---

## 3. VM Summary Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_vms` | List VMs using REST summary API | read_only |
| `vsphere_rest_get_vm` | VM details by VM ID | read_only |
| `vsphere_rest_get_vm_hardware` | VM hardware summary | read_only |
| `vsphere_rest_get_vm_power` | VM power state | read_only |

### Blocked until approval workflow

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_power_on_vm` | Power on VM | approval_required |
| `vsphere_rest_power_off_vm` | Power off VM | approval_required |
| `vsphere_rest_reset_vm` | Reset VM | destructive |
| `vsphere_rest_suspend_vm` | Suspend VM | approval_required |

---

## 4. Host / Cluster / Datastore Summary Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_hosts` | List host summaries | read_only |
| `vsphere_rest_get_host` | Get host detail by ID | read_only |
| `vsphere_rest_list_clusters` | List clusters | read_only |
| `vsphere_rest_get_cluster` | Cluster detail | read_only |
| `vsphere_rest_list_datastores` | List datastores | read_only |
| `vsphere_rest_get_datastore` | Datastore detail | read_only |
| `vsphere_rest_list_networks` | List networks | read_only |

Use pyVmomi for richer details; REST is good for lightweight summaries.

---

## 5. Tagging Tools

Very useful for your platform.

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_tag_categories` | List tag categories | read_only |
| `vsphere_rest_list_tags` | List tags | read_only |
| `vsphere_rest_get_tag_details` | Tag metadata | read_only |
| `vsphere_rest_list_attached_tags` | Tags attached to an object | read_only |
| `vsphere_rest_find_objects_by_tag` | Find VMs/hosts/datastores by tag | read_only |
| `vsphere_rest_attach_tag` | Attach tag to object | approval_required |
| `vsphere_rest_detach_tag` | Detach tag | approval_required |
| `vsphere_rest_create_tag` | Create tag | approval_required |
| `vsphere_rest_delete_tag` | Delete tag | destructive |

Recommended read-only first:

```text
vsphere_rest_list_tags
vsphere_rest_list_attached_tags
vsphere_rest_find_objects_by_tag
```

---

## 6. Content Library Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_content_libraries` | List content libraries | read_only |
| `vsphere_rest_get_content_library` | Content library details | read_only |
| `vsphere_rest_list_library_items` | List items/templates/OVFs | read_only |
| `vsphere_rest_get_library_item` | Library item details | read_only |
| `vsphere_rest_sync_library` | Sync subscribed library | approval_required |
| `vsphere_rest_delete_library_item` | Delete item | destructive |

Useful future prompt:

```text
Show me available VM templates.
```

---

## 7. Storage Policy / PBM Adjacent Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_storage_policies` | List policies if supported | read_only |
| `vsphere_rest_get_storage_policy` | Policy details | read_only |
| `vsphere_rest_find_policy_by_name` | Match StorageClass policy name | read_only |

For robust CSI VA, govmomi/PBM may be stronger.

---

## 8. vCenter Task Tools

| Tool | Purpose | Risk |
|---|---|---:|
| `vsphere_rest_list_recent_tasks` | List recent vCenter tasks | read_only |
| `vsphere_rest_get_task_details` | Task status and errors | read_only |

Useful for:

```text
Why did VM deploy fail?
What recent task failed?
```

---

## 9. Recommended backend endpoints

```text
GET /api/v1/vsphere-rest/about
GET /api/v1/vsphere-rest/appliance/health
GET /api/v1/vsphere-rest/vms
GET /api/v1/vsphere-rest/hosts
GET /api/v1/vsphere-rest/clusters
GET /api/v1/vsphere-rest/datastores
GET /api/v1/vsphere-rest/networks
GET /api/v1/vsphere-rest/tags
GET /api/v1/vsphere-rest/tags/attached?object_id=<id>
GET /api/v1/vsphere-rest/content-libraries
GET /api/v1/vsphere-rest/tasks/recent
```

---

## Recommended first REST tools

```text
1. vsphere_rest_get_vcenter_info
2. vsphere_rest_list_tags
3. vsphere_rest_list_attached_tags
4. vsphere_rest_find_objects_by_tag
5. vsphere_rest_list_content_libraries
6. vsphere_rest_list_library_items
7. vsphere_rest_list_recent_tasks
```

These add features pyVmomi inventory tools do not cover nicely.
