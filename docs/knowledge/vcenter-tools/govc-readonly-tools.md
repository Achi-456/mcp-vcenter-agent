# govc Tools — Read-Only vSphere CLI Fallback

## Purpose

`govc` should be used as a read-only diagnostic fallback for AgenticOps.

Recommended flow:

```text
Agent Engine → Tool Registry → FastAPI govc_service.py → Whitelisted govc command → vCenter
```

Important:

```text
Do NOT expose raw/free-form govc_command to the chatbot.
Only expose safe, whitelisted read-only commands.
```

---

## 1. Safe govc command whitelist

Allow only these command families:

```text
about
ls
find
vm.info
host.info
datastore.info
events
volume.ls
```

Block all destructive or state-changing commands.

---

## 2. Connection / About Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_about` | `govc about -json` | vCenter version/build/API summary | read_only |
| `govc_session_status` | `govc session.ls` | Session check if supported | read_only |

---

## 3. Inventory Discovery Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_ls_root` | `govc ls /` | List root inventory | read_only |
| `govc_find_all` | `govc find /` | Find all inventory objects | read_only |
| `govc_find_vms` | `govc find / -type m` | List VM inventory paths | read_only |
| `govc_find_hosts` | `govc find / -type h` | List ESXi host paths | read_only |
| `govc_find_networks` | `govc find / -type n` | List networks | read_only |

---

## 4. VM Diagnostic Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_vm_info` | `govc vm.info -json <vm>` | Detailed VM info | read_only |
| `govc_vm_info_text` | `govc vm.info <vm>` | Human-readable VM info | read_only |
| `govc_find_vm_by_name` | `govc find / -type m -name <name>` | Find VM path | read_only |

Recommended usage:

```text
Use govc_vm_info as fallback when pyVmomi get_vm_details fails or returns incomplete data.
```

---

## 5. Host Diagnostic Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_host_info` | `govc host.info -json <host>` | ESXi host details | read_only |
| `govc_host_info_text` | `govc host.info <host>` | Human-readable host info | read_only |
| `govc_find_host_by_name` | `govc find / -type h -name <name>` | Find host path | read_only |

Recommended usage:

```text
Use govc_host_info as fallback for: get details for esxi01.dclab.com
```

---

## 6. Datastore Diagnostic Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_datastore_info` | `govc datastore.info -json` | Datastore capacity/type/accessibility | read_only |
| `govc_datastore_info_one` | `govc datastore.info -json <datastore>` | Single datastore detail | read_only |
| `govc_datastore_ls` | `govc datastore.ls -ds=<datastore>` | Browse datastore path read-only | read_only |

Blocked:

```text
govc datastore.rm
govc datastore.cp
govc datastore.mv
```

---

## 7. Events Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_events` | `govc events -json` | Recent vCenter events | read_only |
| `govc_events_for_object` | `govc events -json <object>` | Events for VM/host/datastore | read_only |

---

## 8. CNS / CSI / Volume Tools

| Tool | govc command | Purpose | Risk |
|---|---|---|---:|
| `govc_volume_ls` | `govc volume.ls -json` | List CNS volumes if supported | read_only |
| `govc_volume_ls_datastore` | `govc volume.ls -json -ds=<datastore>` | List volumes on datastore | read_only |
| `govc_volume_info` | if available in installed govc version | CNS volume details | read_only |

Use case:

```text
CSI VA Check:
Kubernetes PV volumeHandle → govc volume.ls → Match CNS volume → Map to datastore
```

---

## 9. Disabled / Blocked govc Tools

| Command | Reason | Risk |
|---|---|---:|
| `govc vm.power` | Changes VM power state | approval_required |
| `govc vm.destroy` | Deletes VM | destructive |
| `govc snapshot.create` | Creates snapshot | approval_required |
| `govc snapshot.remove` | Deletes snapshot | destructive |
| `govc snapshot.revert` | Reverts VM state | destructive |
| `govc vm.migrate` | vMotion / migration | approval_required |
| `govc host.maintenance.enter` | Host maintenance | approval_required |
| `govc host.maintenance.exit` | Host maintenance | approval_required |
| `govc datastore.rm` | Deletes datastore files | destructive |
| `govc object.destroy` | Deletes object | destructive |
| `govc import.ova` | Creates VM/imports OVA | approval_required |
| `govc volume.rm` | Deletes CNS volume | destructive |

---

## 10. Backend endpoints to expose

```text
GET /api/v1/govc/about
GET /api/v1/govc/find-vms
GET /api/v1/govc/find-hosts
GET /api/v1/govc/vm-info?name=<vm>
GET /api/v1/govc/host-info?name=<host>
GET /api/v1/govc/datastore-info
GET /api/v1/govc/events
GET /api/v1/govc/volume-ls
```

Do not expose:

```text
POST /api/v1/govc/command
```

unless it enforces the whitelist strictly.

---

## Recommended first govc tools

```text
1. govc_about
2. govc_vm_info
3. govc_host_info
4. govc_datastore_info
5. govc_events
6. govc_volume_ls
```
