Yes Achintha — now create **Phase 1.3: Real vCenter Inventory**.

This phase should connect your Inventory page to real vCenter data using the credentials saved in Phase 1.2. Since Phase 1.2 already added Kubernetes Secret storage, `/api/v1/connections/*` endpoints, pyVmomi, RBAC, and safe credential handling, Phase 1.3 should **reuse that foundation** instead of asking the user to enter credentials again. 

---

# Phase 1.3 — Real vCenter Inventory

```text id="7uipve"
Phase 1.3 Goal:
Use the saved vCenter Kubernetes Secret to connect to vCenter,
collect real VM, host, datastore, network, cluster, and summary data,
then display it in the Next.js Inventory dashboard.
```

---

# 1. What Phase 1.3 must deliver

At the end of Phase 1.3, this flow should work:

```text id="qjz5gl"
User opens Inventory page
        ↓
Frontend calls FastAPI inventory endpoints
        ↓
FastAPI reads saved vCenter credentials from Kubernetes Secret
        ↓
FastAPI connects to vCenter using pyVmomi
        ↓
FastAPI collects VM / Host / Datastore / Network data
        ↓
FastAPI returns safe structured JSON
        ↓
Frontend displays real tables, summary cards, filters, and refresh button
```

Important rule:

```text id="wacrn7"
Inventory page must not ask for vCenter username/password.
It must use credentials already saved in Phase 1.2.
```

---

# 2. Phase 1.3 scope

## In scope

```text id="0mrktm"
✅ Real VM inventory from vCenter
✅ Real host inventory from vCenter
✅ Real datastore inventory from vCenter
✅ Real network inventory from vCenter
✅ Cluster summary data
✅ Inventory overview cards
✅ Frontend table wiring
✅ Loading states
✅ Empty states
✅ Error states
✅ Refresh button
✅ Safe response schemas
✅ Backend caching with Redis optional
✅ Backend timeout handling
✅ Friendly error messages
✅ No secret values returned to frontend
```

## Out of scope

```text id="fc93iu"
❌ VM power on/off
❌ Delete VM
❌ Create VM
❌ Migrate VM
❌ Snapshot operations
❌ Host maintenance mode
❌ Datastore modification
❌ Approval workflow
❌ Agent auto-actions
❌ Long-term RAG memory
```

Phase 1.3 is **read-only only**.

---

# 3. Recommended endpoint design

Add a new FastAPI router:

```text id="v7z3bs"
apps/backend/app/api/routes/inventory.py
```

Base path:

```text id="b0438x"
/api/v1/inventory
```

Endpoints:

```http id="q1263f"
GET /api/v1/inventory/overview
GET /api/v1/inventory/vms
GET /api/v1/inventory/vms/{vm_id}
GET /api/v1/inventory/hosts
GET /api/v1/inventory/hosts/{host_id}
GET /api/v1/inventory/datastores
GET /api/v1/inventory/datastores/{datastore_id}
GET /api/v1/inventory/networks
GET /api/v1/inventory/clusters
GET /api/v1/inventory/refresh
```

For Phase 1.3 minimum, implement these first:

```text id="ay880p"
GET /api/v1/inventory/overview
GET /api/v1/inventory/vms
GET /api/v1/inventory/hosts
GET /api/v1/inventory/datastores
GET /api/v1/inventory/networks
```

---

# 4. Backend file structure

Add these files:

```text id="b5p025"
apps/backend/
├── app/api/
│   ├── routes/
│   │   └── inventory.py
│   └── schemas/
│       └── inventory.py
│
├── app/services/
│   ├── vcenter_inventory_service.py
│   ├── vcenter_client_factory.py
│   └── inventory_cache_service.py
│
└── app/core/
    └── inventory_errors.py
```

Purpose:

```text id="hlepmo"
inventory.py
    FastAPI inventory routes

schemas/inventory.py
    Pydantic response models for VMs, hosts, datastores, networks

vcenter_client_factory.py
    Reads vCenter Secret and creates pyVmomi connection

vcenter_inventory_service.py
    Collects inventory data from vCenter

inventory_cache_service.py
    Optional Redis cache for inventory responses

inventory_errors.py
    Friendly inventory error mapping
```

---

# 5. Reuse Phase 1.2 credential secret

Phase 1.2 stores this secret:

```text id="iayjnz"
agentic-vcenter-default
```

Keys:

```text id="2h4ur8"
VCENTER_NAME
VCENTER_URL
VCENTER_USERNAME
VCENTER_PASSWORD
VCENTER_VERIFY_SSL
VCENTER_CREATED_AT
VCENTER_UPDATED_AT
VCENTER_LAST_TEST_STATUS
VCENTER_LAST_TESTED_AT
```

Phase 1.3 backend should read:

```text id="d0lq6b"
VCENTER_URL
VCENTER_USERNAME
VCENTER_PASSWORD
VCENTER_VERIFY_SSL
```

Do not return them to frontend.

---

# 6. Backend inventory connection flow

```text id="fk2wwv"
Inventory endpoint called
        ↓
Check vCenter secret exists
        ↓
If not configured, return 409 VCENTER_NOT_CONFIGURED
        ↓
Read secret from Kubernetes
        ↓
Create pyVmomi connection
        ↓
Collect requested inventory object type
        ↓
Disconnect from vCenter
        ↓
Return safe JSON
```

If vCenter is not configured:

```json id="wse9y0"
{
  "ok": false,
  "error_code": "VCENTER_NOT_CONFIGURED",
  "message": "vCenter credentials are not configured. Please configure vCenter in Settings first."
}
```

Frontend should show:

```text id="9gv34s"
vCenter is not configured.
Go to Settings → vCenter Connection.
```

---

# 7. Inventory response schemas

Create:

```text id="456fhg"
apps/backend/app/api/schemas/inventory.py
```

## VM list response

```json id="i5leie"
{
  "items": [
    {
      "id": "vm-101",
      "name": "agentic-worker-01",
      "power_state": "poweredOn",
      "cpu": 4,
      "memory_gb": 12,
      "guest_os": "Red Hat Enterprise Linux 8",
      "ip_address": "192.168.10.21",
      "host": "esxi-01.dclab.local",
      "cluster": "dclab-cluster",
      "datastore": "datastore01",
      "tools_status": "toolsOk",
      "uptime_seconds": 86400,
      "path": "DC1/vm/agentic-worker-01"
    }
  ],
  "count": 1,
  "source": "vcenter",
  "cached": false,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

## Host list response

```json id="s6fqxo"
{
  "items": [
    {
      "id": "host-21",
      "name": "esxi-01.dclab.local",
      "connection_state": "connected",
      "power_state": "poweredOn",
      "cpu_cores": 24,
      "cpu_threads": 48,
      "memory_gb": 128,
      "vm_count": 18,
      "vendor": "Dell Inc.",
      "model": "PowerEdge",
      "version": "8.0.3",
      "cluster": "dclab-cluster"
    }
  ],
  "count": 1,
  "source": "vcenter",
  "cached": false,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

## Datastore list response

```json id="982gcp"
{
  "items": [
    {
      "id": "datastore-33",
      "name": "datastore01",
      "type": "VMFS",
      "capacity_gb": 1024,
      "free_gb": 430,
      "used_gb": 594,
      "used_percent": 58,
      "accessible": true,
      "multiple_host_access": true
    }
  ],
  "count": 1,
  "source": "vcenter",
  "cached": false,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

## Network list response

```json id="7c7r53"
{
  "items": [
    {
      "id": "network-44",
      "name": "VM Network",
      "type": "Network",
      "accessible": true
    }
  ],
  "count": 1,
  "source": "vcenter",
  "cached": false,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

## Overview response

```json id="6qzckb"
{
  "vms": {
    "total": 24,
    "powered_on": 18,
    "powered_off": 6,
    "suspended": 0
  },
  "hosts": {
    "total": 3,
    "connected": 3,
    "maintenance": 0,
    "disconnected": 0
  },
  "datastores": {
    "total": 4,
    "capacity_gb": 4096,
    "free_gb": 1500,
    "used_percent": 63
  },
  "networks": {
    "total": 8
  },
  "source": "vcenter",
  "cached": false,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

---

# 8. Backend service design

## `vcenter_client_factory.py`

Responsibilities:

```text id="0tbkw1"
Read vCenter Secret
Validate required keys exist
Parse vCenter URL
Create SSL context based on VCENTER_VERIFY_SSL
Connect using pyVmomi SmartConnect
Return service instance
Disconnect safely
```

Recommended functions:

```text id="p0zb7o"
get_vcenter_credentials()
connect_to_vcenter()
disconnect_from_vcenter()
with_vcenter_connection()
```

Important:

```text id="l8ts7t"
Always disconnect after request.
Never log password.
Never return credential object to route response.
```

---

## `vcenter_inventory_service.py`

Responsibilities:

```text id="4glxae"
list_vms()
get_vm_detail(vm_id)
list_hosts()
get_host_detail(host_id)
list_datastores()
get_datastore_detail(datastore_id)
list_networks()
list_clusters()
get_inventory_overview()
```

Use pyVmomi container views:

```text id="53cmb5"
vim.VirtualMachine
vim.HostSystem
vim.Datastore
vim.Network
vim.ClusterComputeResource
```

Recommended helper:

```text id="buk0fo"
create_container_view(content, vim_type)
```

---

# 9. Inventory fields to collect

## VM fields

```text id="nhybbh"
id
name
power_state
cpu
memory_gb
guest_os
ip_address
host
cluster
datastore
tools_status
uptime_seconds
path
```

Important safe handling:

```text id="by6w67"
Some VMs may not have IP address.
Some VMs may not have VMware Tools.
Some VMs may not have datastore info.
Never crash because one field is missing.
```

Use safe fallbacks:

```text id="hhbn9e"
ip_address: null
tools_status: "unknown"
datastore: null
host: null
cluster: null
```

---

## Host fields

```text id="kcx0m1"
id
name
connection_state
power_state
cpu_cores
cpu_threads
memory_gb
vm_count
vendor
model
version
cluster
```

---

## Datastore fields

```text id="ryhd0d"
id
name
type
capacity_gb
free_gb
used_gb
used_percent
accessible
multiple_host_access
```

---

## Network fields

```text id="ykkns7"
id
name
type
accessible
```

For distributed switches later:

```text id="snoqae"
portgroup_key
vlan_id
switch_name
```

But that can wait.

---

# 10. Error handling plan

Add friendly error codes:

```text id="731l49"
VCENTER_NOT_CONFIGURED
VCENTER_SECRET_INVALID
VCENTER_AUTH_FAILED
VCENTER_UNREACHABLE
VCENTER_SSL_ERROR
VCENTER_SESSION_EXPIRED
VCENTER_INVENTORY_ERROR
VCENTER_TIMEOUT
INVENTORY_UNKNOWN_ERROR
```

Example response:

```json id="3wj6ne"
{
  "ok": false,
  "error_code": "VCENTER_NOT_CONFIGURED",
  "message": "vCenter credentials are not configured. Please configure vCenter in Settings first."
}
```

Frontend should map them to clear UI messages:

```text id="kedx2u"
VCENTER_NOT_CONFIGURED
    Show Settings button

VCENTER_AUTH_FAILED
    Show "Credentials may be invalid. Update Settings."

VCENTER_UNREACHABLE
    Show "Cannot reach vCenter from FastAPI pod."

VCENTER_SSL_ERROR
    Show "SSL verification failed. Disable Verify SSL for self-signed lab certificates."

VCENTER_TIMEOUT
    Show "vCenter inventory request timed out."
```

---

# 11. Caching plan

For Phase 1.3, inventory can be cached for a short time.

Recommended Redis cache TTL:

```text id="mhviu8"
Overview:      15 seconds
VMs:           30 seconds
Hosts:         30 seconds
Datastores:    60 seconds
Networks:      60 seconds
```

Why cache?

```text id="173efu"
Avoid hitting vCenter every time user switches tabs.
Make UI faster.
Reduce load on vCenter.
```

Cache keys:

```text id="n5ajub"
inventory:overview
inventory:vms
inventory:hosts
inventory:datastores
inventory:networks
```

Response should include:

```json id="6mt7rf"
{
  "cached": true,
  "collected_at": "2026-05-07T12:00:00Z"
}
```

Add refresh option:

```http id="q6zb6k"
GET /api/v1/inventory/vms?refresh=true
```

or:

```http id="7u9z9k"
POST /api/v1/inventory/refresh
```

For simplicity:

```text id="pdn1h3"
Use ?refresh=true in Phase 1.3.
```

---

# 12. Frontend inventory page requirements

Update:

```text id="lymsba"
apps/frontend/app/inventory/page.tsx
apps/frontend/lib/api.ts
```

Optional components:

```text id="jz1srj"
apps/frontend/components/inventory/
├── inventory-overview-cards.tsx
├── vm-table.tsx
├── host-table.tsx
├── datastore-table.tsx
├── network-table.tsx
├── inventory-error-card.tsx
├── inventory-empty-state.tsx
└── refresh-button.tsx
```

---

# 13. Frontend API client functions

Add to:

```text id="05q3nq"
apps/frontend/lib/api.ts
```

Functions:

```text id="gukg4f"
getInventoryOverview()
getInventoryVMs({ refresh?: boolean })
getInventoryHosts({ refresh?: boolean })
getInventoryDatastores({ refresh?: boolean })
getInventoryNetworks({ refresh?: boolean })
getVMDetail(vmId)
getHostDetail(hostId)
getDatastoreDetail(datastoreId)
```

---

# 14. Inventory UI layout

The Inventory page should look like this:

```text id="87erfe"
Page Header:
Inventory
vCenter resource browser

Top row:
[Total VMs] [Powered On] [Hosts] [Datastore Used %] [Networks]

Toolbar:
Search input | Refresh button | Last collected time | Cached badge

Tabs:
VMs | Hosts | Datastores | Networks | Clusters later

Table:
Real inventory data
```

---

# 15. VM table design

Columns:

```text id="v7r2eg"
Name
Power State
CPU
Memory
Guest OS
IP Address
Host
Datastore
Tools
```

Power badge colors:

```text id="kdwap4"
poweredOn     green
poweredOff    gray
suspended     amber
unknown       red/gray
```

Tools badge colors:

```text id="ax7a9q"
toolsOk           green
toolsOld          amber
toolsNotRunning   red
unknown           gray
```

Actions:

```text id="pyzkuy"
View details
Copy name
Copy IP
```

Do not include:

```text id="w5rrmu"
Power On
Power Off
Delete
Snapshot
Migrate
```

---

# 16. Host table design

Columns:

```text id="thnkhc"
Name
Connection
Power
CPU Cores
Memory
VM Count
Version
Cluster
```

Status badges:

```text id="qt5thf"
connected       green
maintenance     amber
disconnected    red
notResponding   red
```

---

# 17. Datastore table design

Columns:

```text id="jtoxtu"
Name
Type
Capacity
Free
Used %
Accessible
Shared
```

Used percentage visual:

```text id="6ezfer"
0–70%      green/normal
70–85%     amber
85–100%    red
```

Use progress bar.

---

# 18. Network table design

Columns:

```text id="iubnvu"
Name
Type
Accessible
```

Later add:

```text id="40imf2"
VLAN
Portgroup
Distributed switch
Connected VMs
```

---

# 19. Loading / empty / error states

## Loading

```text id="3m4wun"
Loading vCenter inventory...
```

Use skeleton rows or simple text.

## Empty

```text id="0ifh4u"
No VMs found.
vCenter returned zero virtual machines.
```

## Not configured

```text id="tzbciq"
vCenter is not configured.
Configure vCenter credentials in Settings before browsing inventory.

Button: Open Settings
```

## API 404 cleanup

Do not show raw:

```text id="4wzrpm"
API 404: {"detail":"Not Found"}
```

Instead show:

```text id="c21kfv"
Inventory API is not available yet.
Check FastAPI inventory router deployment.
```

After Phase 1.3, this should disappear.

---

# 20. Backend route behavior

## `GET /api/v1/inventory/vms`

Steps:

```text id="qssnpe"
1. Check cache unless refresh=true
2. If cache exists, return cached VM list
3. Read vCenter credentials from Kubernetes Secret
4. Connect to vCenter
5. Create container view for vim.VirtualMachine
6. Convert each VM to safe JSON
7. Store result in Redis cache
8. Return response
```

## `GET /api/v1/inventory/hosts`

Steps:

```text id="k1kxk2"
1. Check cache unless refresh=true
2. Read vCenter credentials
3. Connect to vCenter
4. Create container view for vim.HostSystem
5. Convert each host to safe JSON
6. Return response
```

## `GET /api/v1/inventory/datastores`

Steps:

```text id="c4w8r6"
1. Read credentials
2. Connect to vCenter
3. Create container view for vim.Datastore
4. Calculate capacity/free/used
5. Return response
```

## `GET /api/v1/inventory/overview`

Steps:

```text id="679kea"
1. Get VMs, hosts, datastores, networks
2. Calculate summary
3. Return overview cards data
```

---

# 21. Timeout rules

Set timeouts so dashboard does not hang.

Recommended:

```text id="jsa4a8"
vCenter connect timeout: 10 seconds
Inventory query timeout: 30 seconds
Frontend request timeout: 35 seconds
```

If timeout occurs:

```json id="hvfdh6"
{
  "ok": false,
  "error_code": "VCENTER_TIMEOUT",
  "message": "vCenter inventory request timed out."
}
```

---

# 22. Security rules

Phase 1.3 must follow these rules:

```text id="cdypnj"
✅ Inventory endpoints are read-only
✅ No VM modification methods
✅ No power operations
✅ No snapshot operations
✅ No datastore modification
✅ No secret values in responses
✅ No password/API key logs
✅ vCenter credentials read only inside backend
✅ Frontend never receives credentials
✅ Errors are friendly, not raw stack traces
```

Also avoid exposing unnecessary sensitive VM metadata:

```text id="0uzv11"
Do not return full annotation/notes by default
Do not return guest usernames
Do not return advanced config values
Do not return custom fields unless needed
```

---

# 23. Kubernetes / deployment changes

Backend already has service account and RBAC from Phase 1.2. Phase 1.3 may need only code deployment.

Check:

```bash id="6yzvhu"
kubectl get deploy -n agentic-app
kubectl get pods -n agentic-app
kubectl logs deploy/agentic-api -n agentic-app --tail=100
```

Confirm FastAPI can read vCenter secret:

```bash id="c8o7f3"
kubectl auth can-i get secret/agentic-vcenter-default \
  --as=system:serviceaccount:agentic-app:agentic-api \
  -n agentic-app
```

Expected:

```text id="kxwk1n"
yes
```

---

# 24. CI/CD checks

Backend:

```bash id="rzszxn"
cd apps/backend
pytest
```

Frontend:

```bash id="bmyvhp"
cd apps/frontend
npm run lint
npm run build
```

Docker build:

```bash id="n7y92a"
docker build -t agentic-backend:test apps/backend
docker build -t agentic-frontend:test apps/frontend
```

After deploy:

```bash id="y93fah"
kubectl rollout status deploy/agentic-api -n agentic-app
kubectl rollout status deploy/agentic-nextjs -n agentic-app
```

---

# 25. Manual API test plan

## Test 1 — vCenter not configured

Delete secret temporarily only if safe:

```bash id="f5ng7w"
kubectl delete secret agentic-vcenter-default -n agentic-app
```

Call:

```bash id="xrn0mg"
curl -k https://api.dclab.local/api/v1/inventory/vms
```

Expected:

```json id="br01yn"
{
  "ok": false,
  "error_code": "VCENTER_NOT_CONFIGURED"
}
```

Then re-save credentials from Settings.

---

## Test 2 — VM list

```bash id="7ufrq2"
curl -k https://api.dclab.local/api/v1/inventory/vms
```

Expected:

```json id="h0wy95"
{
  "items": [],
  "count": 0,
  "source": "vcenter",
  "cached": false,
  "collected_at": "..."
}
```

If you have VMs, `items` should contain real VM data.

---

## Test 3 — Hosts

```bash id="41676t"
curl -k https://api.dclab.local/api/v1/inventory/hosts
```

Expected:

```text id="5lb5u9"
Real ESXi hosts returned.
```

---

## Test 4 — Datastores

```bash id="jzd6q5"
curl -k https://api.dclab.local/api/v1/inventory/datastores
```

Expected:

```text id="fnoqyd"
Real datastore capacity/free/used values returned.
```

---

## Test 5 — Refresh cache

```bash id="439kty"
curl -k "https://api.dclab.local/api/v1/inventory/vms?refresh=true"
```

Expected:

```text id="wk3w35"
cached: false
```

Call again without refresh:

```bash id="e9ouya"
curl -k https://api.dclab.local/api/v1/inventory/vms
```

Expected:

```text id="42da0w"
cached: true
```

---

# 26. Frontend manual test plan

## Test 1 — Inventory page loads

Open:

```text id="4vxg2x"
https://infra-agent-console.dclab.local/inventory
```

Expected:

```text id="4oj6r9"
No 404 error.
Overview cards load.
VM tab selected.
```

## Test 2 — VM table

Expected:

```text id="3l84gk"
Real VM names appear.
Power state badges show correct colors.
CPU and memory columns show correctly.
Host and datastore columns show values.
```

## Test 3 — Host tab

Expected:

```text id="6aswzw"
ESXi host names appear.
Connection status visible.
CPU/memory/VM count visible.
```

## Test 4 — Datastore tab

Expected:

```text id="1o00y7"
Datastore names appear.
Capacity/free/used percent visible.
Progress bars render correctly.
```

## Test 5 — Refresh button

Expected:

```text id="m81iov"
Click Refresh
        ↓
Button shows loading
        ↓
Data reloads
        ↓
Last collected time updates
```

## Test 6 — Not configured state

Expected:

```text id="l1eg35"
If vCenter secret missing:
    Inventory page shows Settings button
    No raw API error shown
```

---

# 27. Backend unit tests

Add tests for:

```text id="9ucr9t"
vCenter secret missing returns VCENTER_NOT_CONFIGURED
secret exists but missing password returns VCENTER_SECRET_INVALID
VM conversion handles missing guest info
VM conversion handles missing IP
Host conversion handles missing cluster
Datastore conversion avoids divide-by-zero
Network conversion returns safe fields
Inventory response excludes credentials
Cache hit returns cached=true
refresh=true bypasses cache
```

Critical security test:

```text id="cwfbqk"
Assert response JSON does not contain:
- VCENTER_PASSWORD
- password
- api_key
- secret
```

---

# 28. Frontend checks

At minimum:

```text id="sua85i"
Inventory page renders
VM tab calls /api/v1/inventory/vms
Host tab calls /api/v1/inventory/hosts
Datastore tab calls /api/v1/inventory/datastores
Network tab calls /api/v1/inventory/networks
404 errors are not shown raw
VCENTER_NOT_CONFIGURED shows Settings CTA
Refresh button sends refresh=true
```

---

# 29. Implementation order

Follow this exact order.

## Step 1 — Backend schemas

```text id="4wztpd"
Create inventory.py schemas for overview, VM, host, datastore, network.
```

Done when:

```text id="xh90qg"
FastAPI imports schemas successfully.
```

---

## Step 2 — vCenter client factory

```text id="5j3dha"
Create service that reads agentic-vcenter-default secret
and opens pyVmomi connection.
```

Done when:

```text id="4cenop"
Backend can connect to vCenter using saved credentials.
```

---

## Step 3 — VM inventory service

```text id="dwlh89"
Implement list_vms().
```

Done when:

```text id="v84id0"
GET /api/v1/inventory/vms returns real VM list.
```

---

## Step 4 — Host inventory service

```text id="fw1zxi"
Implement list_hosts().
```

Done when:

```text id="4ae7eu"
GET /api/v1/inventory/hosts returns ESXi hosts.
```

---

## Step 5 — Datastore inventory service

```text id="lh06mz"
Implement list_datastores().
```

Done when:

```text id="x3mf3e"
GET /api/v1/inventory/datastores returns capacity/free/used.
```

---

## Step 6 — Network inventory service

```text id="qeyud9"
Implement list_networks().
```

Done when:

```text id="65gmgr"
GET /api/v1/inventory/networks returns port groups/networks.
```

---

## Step 7 — Overview endpoint

```text id="fl2fbx"
Build summary from VM/host/datastore/network data.
```

Done when:

```text id="8v5glr"
GET /api/v1/inventory/overview returns dashboard card values.
```

---

## Step 8 — Redis cache

```text id="2kng65"
Add short TTL caching for inventory endpoints.
```

Done when:

```text id="j9p9qm"
Second request returns cached=true.
refresh=true bypasses cache.
```

---

## Step 9 — Frontend API client

```text id="fpfrt3"
Update lib/api.ts with inventory functions.
```

Done when:

```text id="sq4v95"
Frontend calls correct /api/v1/inventory endpoints.
```

---

## Step 10 — Inventory UI wiring

```text id="cbsuoa"
Wire tabs, tables, summary cards, loading/error/empty states.
```

Done when:

```text id="3oxaq6"
Inventory page shows real vCenter data without raw errors.
```

---

## Step 11 — Final validation

```text id="hfb6l7"
Run build, deploy, test from browser and curl.
```

Done when:

```text id="15urnz"
No 404.
No secret exposure.
Real data visible.
```

---

# 30. Phase 1.3 acceptance checklist

Use this checklist before closing Phase 1.3:

```text id="787pxd"
[ ] GET /api/v1/inventory/overview works
[ ] GET /api/v1/inventory/vms works
[ ] GET /api/v1/inventory/hosts works
[ ] GET /api/v1/inventory/datastores works
[ ] GET /api/v1/inventory/networks works
[ ] Inventory endpoints read saved vCenter Secret
[ ] Inventory endpoints return VCENTER_NOT_CONFIGURED if secret missing
[ ] VM data shows name, power state, CPU, memory, IP, host, datastore
[ ] Host data shows name, connection state, CPU, memory, VM count
[ ] Datastore data shows capacity, free, used percent
[ ] Network data shows name, type, accessibility
[ ] Frontend Inventory page no longer shows 404
[ ] Overview cards show real counts
[ ] Refresh button works
[ ] Loading state works
[ ] Empty state works
[ ] Error state works
[ ] No credential values appear in responses
[ ] No password appears in logs
[ ] CI/CD builds successfully
[ ] Argo CD deploys successfully
```

---

# 31. Best Codex / Cursor prompt for Phase 1.3

Use this prompt directly:

```text id="q06p4p"
You are working inside my existing vCenter Agentic Ops Platform project.

Current state:
- RKE2 Kubernetes cluster is working.
- CI/CD and Argo CD GitOps are working.
- Frontend app path is apps/frontend.
- Backend app path is apps/backend.
- Frontend hostname is https://infra-agent-console.dclab.local.
- FastAPI API hostname is https://api.dclab.local.
- Ingress uses nginx.
- Phase 1.1 dashboard shell is complete.
- Phase 1.2 Settings & Credentials backend wiring is complete.
- vCenter credentials are stored as Kubernetes Secret: agentic-vcenter-default.
- FastAPI service account is agentic-api.
- Do not rename apps/frontend.
- Do not change the main architecture.
- Do not replace FastAPI, Next.js, LangGraph, Redis, Postgres, Kubernetes, or pyVmomi.

Implement Phase 1.3: Real vCenter Inventory.

Goal:
Use the saved vCenter Kubernetes Secret to connect to vCenter with pyVmomi, collect read-only inventory data, and display it in the existing Next.js Inventory page.

Backend requirements:
1. Add FastAPI router: /api/v1/inventory.
2. Add endpoints:
   - GET /api/v1/inventory/overview
   - GET /api/v1/inventory/vms
   - GET /api/v1/inventory/vms/{vm_id}
   - GET /api/v1/inventory/hosts
   - GET /api/v1/inventory/hosts/{host_id}
   - GET /api/v1/inventory/datastores
   - GET /api/v1/inventory/datastores/{datastore_id}
   - GET /api/v1/inventory/networks
   - GET /api/v1/inventory/clusters
3. Minimum required endpoints for this phase:
   - overview
   - vms
   - hosts
   - datastores
   - networks
4. Create Pydantic schemas for:
   - InventoryOverviewResponse
   - VMInventoryItem
   - HostInventoryItem
   - DatastoreInventoryItem
   - NetworkInventoryItem
   - InventoryListResponse
   - InventoryErrorResponse
5. Create vcenter_client_factory.py:
   - Read Kubernetes Secret agentic-vcenter-default
   - Read VCENTER_URL, VCENTER_USERNAME, VCENTER_PASSWORD, VCENTER_VERIFY_SSL
   - Connect to vCenter using pyVmomi
   - Support verify_ssl=false for self-signed lab vCenter
   - Disconnect safely after request
6. Create vcenter_inventory_service.py:
   - list_vms()
   - list_hosts()
   - list_datastores()
   - list_networks()
   - list_clusters()
   - get_inventory_overview()
7. Use pyVmomi container views:
   - vim.VirtualMachine
   - vim.HostSystem
   - vim.Datastore
   - vim.Network
   - vim.ClusterComputeResource
8. Return safe structured JSON only.
9. Never return or log vCenter password.
10. All inventory operations must be read-only.
11. Add friendly error codes:
   - VCENTER_NOT_CONFIGURED
   - VCENTER_SECRET_INVALID
   - VCENTER_AUTH_FAILED
   - VCENTER_UNREACHABLE
   - VCENTER_SSL_ERROR
   - VCENTER_TIMEOUT
   - VCENTER_INVENTORY_ERROR
   - INVENTORY_UNKNOWN_ERROR
12. Return VCENTER_NOT_CONFIGURED if the secret is missing.
13. Add optional Redis cache with TTL:
   - overview: 15s
   - vms: 30s
   - hosts: 30s
   - datastores: 60s
   - networks: 60s
14. Support refresh=true query parameter to bypass cache.
15. Add tests or safe manual verification.
16. Do not implement power operations, delete operations, snapshot operations, or migration.

Frontend requirements:
1. Update apps/frontend/lib/api.ts with:
   - getInventoryOverview()
   - getInventoryVMs({ refresh?: boolean })
   - getInventoryHosts({ refresh?: boolean })
   - getInventoryDatastores({ refresh?: boolean })
   - getInventoryNetworks({ refresh?: boolean })
   - getVMDetail(vmId)
   - getHostDetail(hostId)
   - getDatastoreDetail(datastoreId)
2. Update apps/frontend/app/inventory/page.tsx.
3. Add overview cards:
   - Total VMs
   - Powered On
   - Hosts
   - Datastore Used %
   - Networks
4. Add tabs:
   - VMs
   - Hosts
   - Datastores
   - Networks
5. VM table columns:
   - Name
   - Power State
   - CPU
   - Memory
   - Guest OS
   - IP Address
   - Host
   - Datastore
   - Tools
6. Host table columns:
   - Name
   - Connection
   - Power
   - CPU Cores
   - Memory
   - VM Count
   - Version
   - Cluster
7. Datastore table columns:
   - Name
   - Type
   - Capacity
   - Free
   - Used %
   - Accessible
   - Shared
8. Network table columns:
   - Name
   - Type
   - Accessible
9. Add refresh button.
10. Add last collected time.
11. Add cached badge when response cached=true.
12. Add search/filter input if simple to implement.
13. Show loading, empty, and friendly error states.
14. Do not show raw API 404 messages.
15. If VCENTER_NOT_CONFIGURED, show button to open Settings.
16. Do not add any dangerous VM actions.

Validation:
1. Run backend tests if available.
2. Run frontend lint/build.
3. Verify curl https://api.dclab.local/api/v1/inventory/vms returns real data.
4. Verify browser https://infra-agent-console.dclab.local/inventory shows real inventory.
5. Verify no response contains VCENTER_PASSWORD or password.
6. Verify no logs expose vCenter password.
7. Verify Inventory page no longer shows API 404.

Expected result:
A read-only real vCenter inventory dashboard showing VMs, hosts, datastores, networks, and overview cards using credentials saved from Phase 1.2.
```

---

# 32. Best final direction

Phase 1.3 should be handled carefully because it is the first time your dashboard becomes truly useful.

Build it in this order:

```text id="ig0j5f"
1. Backend VM list from saved Secret
2. Backend hosts/datastores/networks
3. Overview endpoint
4. Frontend table wiring
5. Friendly error states
6. Redis cache
7. Final security check
```

After Phase 1.3, your platform will have a real foundation:

```text id="04pva5"
Settings page stores credentials
Inventory page displays real vCenter resources
Chat page can later use the same inventory tools
```

Then the next phase should be:

```text id="a9v1ux"
Phase 1.4 — Chat SSE connected to real agent tools
```
