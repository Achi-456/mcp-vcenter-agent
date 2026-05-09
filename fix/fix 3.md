# Fix 3 — Intent Classifier, Object-Type Routing, and Tool Output Correctness

> **Target phase**: Phase 1.4 — Chat SSE Connected to Real Agent Tools  
> **Focus**: Fix host-vs-VM routing, prevent fake empty answers, improve tool trace, and include the Phase 2 improvements needed for stable vCenter sessions.

---

## What this fixes

The current assistant can receive a prompt like:

```text
get details for esxi01.dclab.com
```

but it incorrectly routes the request to:

```text
get_vm_details
```

Then it returns a fake-looking VM table with:

```text
Power State: unknown
Host: N/A
IP Address: N/A
CPU: 0 vCPU
Memory: 0 GB
```

This is wrong because `esxi01.dclab.com` is an ESXi host, not a VM.

This fix also includes important improvements from Phase 2:

1. Persistent vCenter session must not cache authentication failures.
2. `host-details` endpoint must return proper errors, not HTTP 200 with an `error` field.
3. `connect_vcenter` must force a real reconnect.
4. `with_vcenter()` should use the new `VCenterSession` singleton.
5. The classifier must run before generic tool fallback.

---

## Root cause

The failure is not one bug. It is a chain of issues:

| # | Issue | Result |
|---|---|---|
| 1 | Generic `details for (\S+)` regex runs before host detection | `esxi01.dclab.com` is treated as a VM |
| 2 | `get_host_details` endpoint was missing or mapped incorrectly | Host requests fall back to VM endpoint |
| 3 | `get_vm_details` returns empty fake object when no VM is found | Assistant shows misleading N/A table |
| 4 | Failed auth/tool errors are cached | Agent replays stale `NotAuthenticated` failures |
| 5 | vCenter session reconnect logic is weak | Multiple tool calls can fail after session expiry |

---

## Desired behavior

### Prompt A

```text
get details for esxi01.dclab.com
```

Expected routing:

```text
intent: get_host_details
target_type: host
target_name: esxi01.dclab.com
tool: get_host_details
args: {"host_name": "esxi01.dclab.com"}
```

Expected answer:

```text
I found ESXi host esxi01.dclab.com. No action was taken.
```

Then a table with real host details.

---

### Prompt B

```text
inspect roshellevm02
```

Expected routing:

```text
intent: get_vm_details
target_type: vm
target_name: roshellevm02
tool: get_vm_details
args: {"vm_name": "roshellevm02"}
```

---

### Prompt C

```text
turn esxi01.dclab.com maintenance mode
```

Expected routing:

```text
intent: risky_maintenance_operation
risk_level: approval_required
blocked: true
```

No maintenance mode action should execute in Phase 1.4.

---

# Phase 2 Improvements to Include Before Phase 3

These must be included because Phase 3 routing will still fail if the session and cache behavior are unstable.

---

## Improvement 2.1 — Do not cache failed auth/tool results

### Problem

The old behavior cached failed results like:

```text
vim.fault.NotAuthenticated
session is not authenticated
VCENTER_AUTH_FAILED
VCENTER_SESSION_EXPIRED
```

Then the agent reused the cached failure instead of retrying.

### Fix

Update the tool cache logic so failed tool results are never cached.

Do not cache if any of these are true:

```text
HTTP status is not 2xx
response.ok == false
response contains error_code
response contains NotAuthenticated
response contains session is not authenticated
response contains VCENTER_AUTH_FAILED
response contains VCENTER_SESSION_EXPIRED
response contains invalid login
response contains NoPermission
```

### Example helper

```python
def should_cache_tool_result(result: dict, http_status: int | None = None) -> bool:
    if http_status is not None and (http_status < 200 or http_status >= 300):
        return False

    if result.get("ok") is False:
        return False

    if result.get("error_code"):
        return False

    text = str(result).lower()
    blocked = [
        "notauthenticated",
        "session is not authenticated",
        "vcenter_auth_failed",
        "vcenter_session_expired",
        "invalid login",
        "nopermission",
    ]

    return not any(item in text for item in blocked)
```

### Acceptance

```text
A failed NotAuthenticated result must never be replayed from cache.
The agent should reconnect and retry once.
```

---

## Improvement 2.2 — `host-details` must return proper error status

### Problem

A response like this is bad:

```json
{
  "hosts": [],
  "count": 0,
  "error": "Host not found"
}
```

If returned with HTTP 200, the agent may treat it as success.

### Fix

Return proper error JSON and HTTP status.

Example:

```json
{
  "ok": false,
  "error_code": "HOST_NOT_FOUND",
  "message": "No ESXi host named esxi01.dclab.com was found."
}
```

Recommended HTTP status:

```text
404
```

### Acceptance

```text
Missing host should not produce a success tool_result.
It should produce error_code HOST_NOT_FOUND.
```

---

## Improvement 2.3 — Use `VCenterSession` singleton through `with_vcenter()`

### Requirement

Make sure existing callers still work:

```python
with_vcenter(fn)
```

but internally it must use:

```python
vcenter_session.run(fn)
```

### Required behavior

Before every call:

```python
si.content.sessionManager.currentSession
```

If this returns `None`, reconnect.

If `vim.fault.NotAuthenticated` is thrown during a call:

```text
1. Clear session
2. Reconnect
3. Retry once
4. If retry fails, return clean VCENTER_SESSION_EXPIRED
```

### Acceptance

```text
Multiple tools in one chat turn should not fail with NotAuthenticated after the first call.
```

---

## Improvement 2.4 — Do not lock long vCenter calls unless necessary

### Quick version

The first implementation may keep a lock during the full vCenter call for safety.

### Better version

Lock only during:

```text
connect
reconnect
session validation
```

Avoid holding the lock for long inventory reads if possible.

### Phase 3 recommendation

For now, safety is more important than concurrency. It is acceptable to serialize vCenter calls. Add a TODO to optimize lock scope later.

---

## Improvement 2.5 — `connect_vcenter` must force reconnect

### Problem

Old behavior:

```text
connect_vcenter → Already connected
```

but the current session could still be stale.

### Fix

`connect_vcenter` should call:

```python
vcenter_session.force_reconnect()
```

### Endpoint

```http
POST /api/v1/connections/vcenter/reconnect
```

### Acceptance

```text
connect_vcenter should create a fresh valid session, not return a misleading cached state.
```

---

# Phase 3 Implementation Plan

---

## Fix 3.1 — Add object-type classifier

### Goal

Before selecting a tool, classify the target object type:

```text
vm
host
datastore
network
cluster
unknown
```

### Suggested file

```text
apps/engine/app/graph/classifier.py
```

or if the router already exists:

```text
apps/engine/app/tools/router.py
```

### Basic model

```python
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    target_type: str | None = None
    target_name: str | None = None
    tool: str | None = None
    args: dict | None = None
    risk_level: str = "read_only"
    blocked: bool = False
    reason: str | None = None
```

---

## Fix 3.2 — Normalize prompt before classification

### Why

Users may type:

```text
get details for esxi01.dclab.com".
trun roshellevm02 this VM on
show me host details for ESXI01
```

### Normalize function

```python
def normalize_text(text: str) -> str:
    return (
        text.strip()
        .replace('"', '')
        .replace("'", "")
        .replace(".”", "")
        .replace(".", " . ")
        .replace(",", " ")
        .lower()
    )
```

### Entity cleanup

```python
def clean_entity(entity: str) -> str:
    return entity.strip().strip('"').strip("'").strip(".").strip(",")
```

---

## Fix 3.3 — Extract entity correctly

### Patterns to support

```text
get details for esxi01.dclab.com
show host details for esxi01.dclab.com
inspect roshellevm02
show roshellevm02 details
what host is roshellevm02 running on
what VMs are running on esxi01.dclab.com
```

### Example extractor

```python
import re

DETAIL_PATTERNS = [
    r"details for\s+([^\s]+)",
    r"detail for\s+([^\s]+)",
    r"inspect\s+([^\s]+)",
    r"show\s+([^\s]+)\s+details",
    r"host details for\s+([^\s]+)",
    r"vm details for\s+([^\s]+)",
    r"power state of\s+([^\s]+)",
    r"what host is\s+([^\s]+)",
    r"what vms are running on\s+([^\s]+)",
]


def extract_entity(message: str) -> str | None:
    msg = message.strip()
    for pattern in DETAIL_PATTERNS:
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            return clean_entity(match.group(1))
    return None
```

---

## Fix 3.4 — Host detection must run before generic VM routing

### Host-like detection

```python
def is_host_like(entity: str, message: str = "") -> bool:
    e = entity.lower()
    m = message.lower()

    if "host details" in m or "esxi" in m or "host info" in m:
        return True

    host_patterns = [
        "esxi",
        "esx-",
        "esx01",
        ".dclab.com",
        ".dclab.local",
    ]

    return any(pattern in e for pattern in host_patterns)
```

### Important rule

This must run before:

```text
generic details → get_vm_details
```

---

## Fix 3.5 — Risky operation detection must run before all tools

### Risky patterns

```python
RISKY_PATTERNS = {
    "power_operation": [
        "turn on", "trun on", "power on", "start vm", "boot vm",
        "turn off", "trun off", "power off", "shutdown", "shut down",
        "restart", "reboot", "reset", "suspend",
    ],
    "delete_operation": [
        "delete", "remove", "destroy",
    ],
    "snapshot_operation": [
        "delete snapshot", "snapshot delete", "revert snapshot", "restore snapshot",
    ],
    "migration_operation": [
        "migrate", "vmotion", "move vm",
    ],
    "maintenance_operation": [
        "maintenance mode", "enter maintenance", "exit maintenance",
    ],
}


def detect_risky_intent(message: str) -> dict | None:
    msg = message.lower()
    for intent, patterns in RISKY_PATTERNS.items():
        for pattern in patterns:
            if pattern in msg:
                return {
                    "intent": intent,
                    "risk_level": "approval_required",
                    "blocked": True,
                    "matched_pattern": pattern,
                }
    return None
```

### Acceptance

```text
turn esxi01.dclab.com maintenance mode → blocked
trun roshellevm02 this VM on → blocked
power off Achintha-agentic-cp-01 → blocked
```

No vCenter change should execute.

---

## Fix 3.6 — Classifier routing order

Use this order:

```text
1. normalize_prompt
2. detect_risky_intent
3. detect list_tools
4. extract entity
5. detect host/datastore/network/cluster object type
6. detect VM detail intent
7. detect context shortcuts
8. fallback to greeting or clarification
```

### Example classifier

```python
def classify_request(message: str) -> IntentResult:
    normalized = normalize_text(message)

    risky = detect_risky_intent(normalized)
    if risky:
        entity = extract_entity(message)
        return IntentResult(
            intent=risky["intent"],
            target_name=entity,
            risk_level="approval_required",
            blocked=True,
            reason=f"High-risk action detected: {risky['matched_pattern']}",
        )

    if "list tools" in normalized or "tools you have" in normalized or "available tools" in normalized:
        return IntentResult(
            intent="list_tools",
            target_type=None,
            tool="list_available_tools",
            args={},
        )

    entity = extract_entity(message)

    if entity and is_host_like(entity, message):
        return IntentResult(
            intent="get_host_details",
            target_type="host",
            target_name=entity,
            tool="get_host_details",
            args={"host_name": entity},
        )

    if entity and ("details" in normalized or "inspect" in normalized or "power state" in normalized):
        return IntentResult(
            intent="get_vm_details",
            target_type="vm",
            target_name=entity,
            tool="get_vm_details",
            args={"vm_name": entity},
        )

    if "powered off" in normalized:
        return IntentResult(intent="get_powered_off_vms", tool="get_powered_off_vms", args={})

    if "datastore health" in normalized or "datastores above" in normalized:
        return IntentResult(intent="get_datastore_health", tool="get_datastore_health", args={})

    if "active alarms" in normalized or "alarms" in normalized:
        return IntentResult(intent="get_active_alarms", tool="get_active_alarms", args={})

    if "recent events" in normalized or "events" in normalized:
        return IntentResult(intent="get_recent_events", tool="get_recent_events", args={})

    if "rke2" in normalized or "agentic vms" in normalized:
        return IntentResult(intent="get_rke2_vms", tool="get_rke2_vms", args={})

    if "overview" in normalized or "environment" in normalized:
        return IntentResult(intent="environment_overview", tool="get_environment_overview", args={})

    return IntentResult(
        intent="unknown",
        tool=None,
        args={},
        reason="No matching read-only vCenter intent detected.",
    )
```

---

## Fix 3.7 — Add `get_host_details` tool

### Tool metadata

```json
{
  "name": "get_host_details",
  "display_name": "Get Host Details",
  "description": "Get read-only details for a specific ESXi host.",
  "category": "Inventory & Information",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false
}
```

### MCP / Agent dispatch

Tool args:

```json
{
  "host_name": "esxi01.dclab.com"
}
```

Backend endpoint:

```http
GET /api/v1/context/host-details?name=esxi01.dclab.com
```

---

## Fix 3.8 — Add or improve `search_inventory_object`

### Purpose

If the object type is ambiguous, search across inventory.

### Tool metadata

```json
{
  "name": "search_inventory_object",
  "display_name": "Search Inventory Object",
  "description": "Search VMs, hosts, clusters, datastores, and networks by name.",
  "category": "Inventory & Information",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false
}
```

### Response

```json
{
  "query": "esxi01.dclab.com",
  "matches": [
    {
      "type": "host",
      "name": "esxi01.dclab.com",
      "confidence": 0.98
    }
  ]
}
```

### Use cases

```text
get details for unknown-object-name
show details for dclab-ds01
inspect production-network
```

---

## Fix 3.9 — Fix `get_vm_details` not-found behavior

### Current bad behavior

```text
I found esxi01.dclab.com.
Power State: unknown
CPU: 0
Memory: 0 GB
```

### Required behavior

If VM not found:

```json
{
  "ok": false,
  "error_code": "VM_NOT_FOUND",
  "message": "No VM named esxi01.dclab.com was found."
}
```

If the input looks like a host:

```json
{
  "ok": false,
  "error_code": "WRONG_OBJECT_TYPE",
  "message": "esxi01.dclab.com looks like an ESXi host, not a VM.",
  "suggested_tool": "get_host_details"
}
```

### Acceptance

```text
No unknown/N/A/0 fake VM tables should be generated for missing VMs.
```

---

## Fix 3.10 — Answer formatting for host details

When `get_host_details` succeeds, the final answer should be:

```markdown
I found ESXi host **esxi01.dclab.com**. No action was taken.

| Property | Value |
|---|---|
| Connection State | connected |
| Power State | poweredOn |
| Version | ESXi 7.0.3 |
| Build | 00000000 |
| Vendor / Model | Dell Inc. PowerEdge R740 |
| CPU Cores / Threads | 24 / 48 |
| Memory | 128 GB |
| VM Count | 18 |
| Cluster | dclab-cluster |
| Management IP | 172.25.188.23 |

**Suggested next step:**  
I can show VMs running on this host, check recent host events, or summarize active alarms related to it.
```

---

## Fix 3.11 — Answer formatting for wrong object type

If user asks for VM details but the name is host-like:

```markdown
`esxi01.dclab.com` looks like an ESXi host, not a VM.

I will use the host details tool instead of the VM details tool.
```

Then call `get_host_details` if the graph supports tool redirection.

If not, ask the user:

```markdown
Would you like me to inspect it as an ESXi host?
```

---

## Fix 3.12 — SSE events required

For:

```text
get details for esxi01.dclab.com
```

Expected stream:

```text
event: intent
data: {"intent":"get_host_details","target_type":"host","target_name":"esxi01.dclab.com"}

event: safety_check
data: {"risk_level":"read_only","blocked":false}

event: tool_call
data: {"tool":"get_host_details","args":{"host_name":"esxi01.dclab.com"},"status":"running"}

event: tool_result
data: {"tool":"get_host_details","status":"success","summary":"Found ESXi host esxi01.dclab.com"}

event: final
data: {"content":"I found ESXi host **esxi01.dclab.com**. No action was taken..."}

event: done
data: {}
```

For risky prompt:

```text
turn esxi01.dclab.com maintenance mode
```

Expected stream:

```text
event: intent
data: {"intent":"maintenance_operation","target_name":"esxi01.dclab.com"}

event: safety_check
data: {"risk_level":"approval_required","blocked":true}

event: blocked
data: {"message":"Maintenance mode is a high-risk host action and is disabled in Phase 1.4."}

event: done
data: {}
```

---

# Files to Update

Exact paths may vary. Search before editing.

| Area | Likely file |
|---|---|
| Classifier / router | `apps/engine/app/graph/classifier.py` or `apps/engine/app/tools/router.py` |
| LangGraph workflow | `apps/engine/app/graph/workflow.py` |
| Tool registry | `apps/engine/app/tools/registry.py` |
| Tool schemas | `apps/engine/app/tools/schemas.py` |
| MCP dispatch | `apps/mcp/server.py` |
| Context routes | `apps/backend/app/api/routes/context.py` |
| vCenter session | `apps/backend/app/services/vcenter_client_factory.py` |
| Inventory service | `apps/backend/app/services/vcenter_inventory_service.py` |
| SSE hook | `apps/frontend/hooks/use-sse-chat.ts` |
| Assistant panel | `apps/frontend/components/chat/ai-assistant-panel.tsx` |

---

# Implementation Order

Do not do this randomly. Use this exact order.

## Step 1 — Ensure Phase 2 fixes are present

```text
- VCenterSession singleton exists
- with_vcenter delegates to VCenterSession
- NotAuthenticated reconnects and retries once
- failed auth/tool errors are not cached
- host-details endpoint exists
- connect_vcenter force reconnect exists
```

## Step 2 — Fix backend host-details behavior

```text
- /api/v1/context/host-details?name=<host_name>
- proper 404 HOST_NOT_FOUND
- real host fields returned
```

## Step 3 — Add get_host_details tool metadata

```text
- category: Inventory & Information
- risk_level: read_only
- enabled: true
- implemented: true
```

## Step 4 — Fix MCP/agent dispatch

```text
get_host_details {host_name} → /api/v1/context/host-details?name=<host_name>
```

## Step 5 — Add classifier object-type detection

```text
- risky detection first
- host detection before VM detection
- generic details fallback last
```

## Step 6 — Fix get_vm_details not-found behavior

```text
- no fake empty object
- return VM_NOT_FOUND or WRONG_OBJECT_TYPE
```

## Step 7 — Add search_inventory_object

```text
- used when object type is unclear
- searches VMs, hosts, datastores, networks, clusters
```

## Step 8 — Update answer formatting

```text
- host details table
- no action was taken
- suggested next step
```

## Step 9 — Validate with prompts

Run all test prompts below.

---

# Validation Prompts

## Test A — ESXi host details

Prompt:

```text
get details for esxi01.dclab.com
```

Expected:

```text
intent: get_host_details
tool: get_host_details
args: {"host_name":"esxi01.dclab.com"}
```

Must not call:

```text
get_vm_details
```

---

## Test B — Host wording

Prompt:

```text
show host details for esxi01.dclab.com
```

Expected:

```text
get_host_details
```

---

## Test C — VM details

Prompt:

```text
inspect roshellevm02
```

Expected:

```text
get_vm_details
```

---

## Test D — Unknown object

Prompt:

```text
get details for unknown-object-name
```

Expected:

```text
search_inventory_object
```

Then honest not-found response.

---

## Test E — Host risky action

Prompt:

```text
turn esxi01.dclab.com maintenance mode
```

Expected:

```text
blocked high-risk action
```

Must not execute maintenance mode.

---

## Test F — VM risky action typo

Prompt:

```text
trun roshellevm02 this VM on
```

Expected:

```text
blocked high-risk action
```

Must not power on the VM.

---

## Test G — Tool list

Prompt:

```text
list down all the tools you have
```

Expected:

```text
list_available_tools
```

Grouped tool list with read-only tools available and risky tools disabled/approval-required.

---

# Direct API Validation

## Test host-details endpoint

```powershell
$POD = kubectl -n agentic-app get pod -l app=fastapi -o jsonpath="{.items[0].metadata.name}"

kubectl -n agentic-app exec $POD -- curl -s \
  "http://localhost:8000/api/v1/context/host-details?name=esxi01"
```

Expected:

```json
{
  "hosts": [
    {
      "name": "esxi01.dclab.com",
      "connection_state": "connected"
    }
  ],
  "count": 1
}
```

## Test host not found

```powershell
kubectl -n agentic-app exec $POD -- curl -i -s \
  "http://localhost:8000/api/v1/context/host-details?name=not-a-real-host"
```

Expected:

```text
HTTP/1.1 404
```

and:

```json
{
  "ok": false,
  "error_code": "HOST_NOT_FOUND"
}
```

---

# Chat Stream Validation

```powershell
curl.exe -k -N \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message":"get details for esxi01.dclab.com","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' \
  https://api.dclab.local/api/v1/chat/stream
```

Expected sequence:

```text
intent: get_host_details
tool_call: get_host_details
tool_result: success
final: host details table
```

No `get_vm_details` call.

---

# Acceptance Checklist

```text
[ ] Phase 2 session fixes are present
[ ] Failed auth/tool results are not cached
[ ] /api/v1/context/host-details exists
[ ] host-details returns 404 HOST_NOT_FOUND when missing
[ ] get_host_details tool exists in registry
[ ] MCP maps get_host_details to /api/v1/context/host-details
[ ] get_host_details forwards host_name as ?name=
[ ] Classifier detects host-like entities before generic VM details
[ ] Risky operation detection runs before all tool selection
[ ] get_vm_details no longer returns fake empty objects
[ ] search_inventory_object exists or fallback search works
[ ] Prompt “get details for esxi01.dclab.com” calls get_host_details
[ ] Prompt “inspect roshellevm02” calls get_vm_details
[ ] Prompt “turn esxi01.dclab.com maintenance mode” is blocked
[ ] Host details answer uses advanced formatted table
[ ] Suggested next step is shown
[ ] No vCenter password appears in logs or responses
```

---

# Codex Prompt

Use this with Codex from the new Kubernetes project root:

```text
You are working in my new Kubernetes/RKE2 vCenter Agentic Ops Platform.

Current problem:
The agent incorrectly handles prompts like:
get details for esxi01.dclab.com

It calls get_vm_details instead of get_host_details and returns a fake empty VM table with unknown/N/A/0 values.

Fix Phase 3: Intent Classifier, Object-Type Routing, and Tool Output Correctness.

Important Phase 2 improvements must also be included:
1. VCenterSession singleton must be used by with_vcenter().
2. currentSession must be checked before each call.
3. NotAuthenticated must reconnect and retry once.
4. Failed auth/tool errors must not be cached.
5. host-details endpoint must return proper 404 HOST_NOT_FOUND, not HTTP 200 with error field.
6. connect_vcenter must force a real reconnect.

Now implement Phase 3:

1. Add or improve classifier/object-type router.
Target object types:
- vm
- host
- datastore
- network
- cluster
- unknown

2. Routing order must be:
- normalize_prompt
- detect_risky_intent
- detect list_tools
- extract entity
- detect host/datastore/network/cluster object type
- detect VM detail intent
- detect context shortcuts
- fallback to unknown/greeting

3. Host detection must happen before generic VM detail routing.
Host rules:
- entity starts with esxi or esx-
- entity contains .dclab.com or .dclab.local and matches known host inventory
- prompt contains host details, ESXi, host info
- if ambiguous, search both host and VM inventories

4. Add or fix get_host_details tool.
Metadata:
name: get_host_details
display_name: Get Host Details
category: Inventory & Information
risk_level: read_only
enabled: true
implemented: true
requires_approval: false

Tool args:
{"host_name":"esxi01.dclab.com"}

Backend endpoint:
GET /api/v1/context/host-details?name=<host_name>

5. Add or fix /api/v1/context/host-details.
Return:
- name
- connection_state
- power_state
- version
- build
- vendor
- model
- cpu_cores
- cpu_threads
- memory_gb
- vm_count
- cluster
- management_ip if available
- path or moid if available
- alarms_count if available

If not found, return HTTP 404:
{
  "ok": false,
  "error_code": "HOST_NOT_FOUND",
  "message": "No ESXi host named <name> was found."
}

6. Fix get_vm_details.
If no VM is found, do not return fake unknown/N/A/0 data.
Return:
{
  "ok": false,
  "error_code": "VM_NOT_FOUND",
  "message": "No VM named <name> was found."
}

If the input looks like a host, return:
{
  "ok": false,
  "error_code": "WRONG_OBJECT_TYPE",
  "message": "<name> looks like an ESXi host, not a VM.",
  "suggested_tool": "get_host_details"
}

7. Add search_inventory_object if missing.
It should search VMs, hosts, datastores, networks, and clusters.
Return typed matches with confidence.

8. Add risky operation detection before tool execution.
Block:
- power on/off
- turn on/off including typo trun
- reboot/reset/shutdown
- delete/remove/destroy
- snapshot delete/revert
- migrate/vMotion
- maintenance mode

If risky, emit blocked event and do not execute vCenter mutation.

9. Update SSE events.
For host detail prompt, stream:
- intent
- safety_check
- tool_call
- tool_result
- final
- done

10. Update final answer formatting.
For host details:
“I found ESXi host <host_name>. No action was taken.”
Then a Markdown table:
- Connection State
- Power State
- Version
- Build
- Vendor / Model
- CPU Cores / Threads
- Memory
- VM Count
- Cluster
- Management IP

Then:
Suggested next step:
“I can show VMs running on this host, check recent host events, or summarize active alarms related to it.”

11. Validate with these prompts:
- get details for esxi01.dclab.com → get_host_details
- show host details for esxi01.dclab.com → get_host_details
- inspect roshellevm02 → get_vm_details
- get details for unknown-object-name → search_inventory_object then not found
- turn esxi01.dclab.com maintenance mode → blocked
- trun roshellevm02 this VM on → blocked
- list down all the tools you have → list_available_tools

Expected result:
The assistant correctly distinguishes ESXi hosts from VMs, uses get_host_details for host prompts, stops returning fake empty VM tables, blocks high-risk actions, and keeps all vCenter operations read-only in Phase 1.4.
```

---

# Final Notes

Phase 3 should not add real mutation tools.

Do not implement:

```text
power_on_vm
power_off_vm
maintenance mode
snapshot delete
migration
host reboot
```

Those can remain visible in the tool registry as:

```text
requires_approval: true
enabled: false
implemented: false
phase: future
```

Phase 3 is about correct routing, safer outputs, and better read-only assistant intelligence.
