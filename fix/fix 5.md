# Fix 5 — vCenter Tools in Agent

> **Phase**: 1.4 / Fix 5  
> **Focus**: Real read-only vCenter tools inside the Agent Engine  
> **Scope**: Tool registry, `ToolSpec`, `RiskLevel`, core vCenter tools, Redis tool-result cache

---

## 1. Goal

Build a proper **vCenter tool layer** inside the Agent Engine so the AI Assistant can call real, safe, read-only infrastructure tools instead of relying on hardcoded routing or direct frontend context calls.

Main flow:

```text
User asks natural-language infrastructure question
        ↓
Agent classifies intent
        ↓
Agent selects a registered ToolSpec
        ↓
Tool executes through FastAPI/vCenter backend
        ↓
Tool result is cached safely in Redis
        ↓
LLM receives user message + tool result JSON
        ↓
Assistant returns advanced answer with tool trace
```

---

## 2. What Fix 5 should deliver

```text
✅ ToolSpec schema
✅ RiskLevel enum
✅ ToolCategory enum or category field
✅ Tool registry
✅ list_vms tool
✅ get_vm_details tool
✅ list_hosts tool
✅ list_datastores tool
✅ Redis-backed tool result cache
✅ Cache bypass support
✅ Safe cache rules
✅ Tool trace output
✅ Tests for each tool
```

---

## 3. Important rule

Fix 5 must remain **read-only**.

Allowed:

```text
✅ list VMs
✅ get VM details
✅ list hosts
✅ list datastores
✅ inspect inventory
✅ cache successful read-only results
```

Not allowed in this phase:

```text
❌ power on VM
❌ power off VM
❌ reboot VM
❌ delete VM
❌ create VM
❌ migrate VM
❌ host maintenance mode
❌ datastore modification
❌ network modification
```

Dangerous tools may exist in the registry later, but for Fix 5 they must not execute.

---

## 4. Target file structure

Recommended Agent Engine structure:

```text
apps/engine/
└── app/
    ├── tools/
    │   ├── __init__.py
    │   ├── schemas.py
    │   ├── registry.py
    │   ├── cache.py
    │   └── vcenter_tools.py
    │
    ├── graph/
    │   ├── workflow.py
    │   ├── nodes.py
    │   └── state.py
    │
    ├── safety/
    │   └── policy.py
    │
    └── main.py
```

If these files already exist, update them instead of creating duplicates.

---

## 5. ToolSpec design

Create or improve:

```text
apps/engine/app/tools/schemas.py
```

Recommended model:

```python
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    APPROVAL_REQUIRED = "approval_required"
    DESTRUCTIVE = "destructive"


class ToolCategory(str, Enum):
    INVENTORY = "Inventory & Information"
    VM_MANAGEMENT = "VM Management"
    SNAPSHOT = "VM Snapshots"
    HOST_MANAGEMENT = "Host Management"
    MONITORING = "Monitoring & Events"
    GENERAL = "General & Utility"


class ToolSpec(BaseModel):
    name: str
    display_name: str
    description: str
    category: ToolCategory
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    enabled: bool = True
    implemented: bool = True
    requires_approval: bool = False
    cache_ttl_seconds: int = 30
    backend_endpoint: Optional[str] = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
```

Example:

```python
ToolSpec(
    name="get_vm_details",
    display_name="Get VM Details",
    description="Get read-only details for a specific VM.",
    category=ToolCategory.INVENTORY,
    risk_level=RiskLevel.READ_ONLY,
    enabled=True,
    implemented=True,
    requires_approval=False,
    cache_ttl_seconds=30,
    backend_endpoint="/api/v1/context/vm-details",
    input_schema={
        "type": "object",
        "properties": {"vm_name": {"type": "string"}},
        "required": ["vm_name"],
    },
)
```

---

## 6. Tool registry

Create or improve:

```text
apps/engine/app/tools/registry.py
```

Required functions:

```python
def register_tool(spec, executor) -> None:
    ...

def get_tool(name: str):
    ...

def list_tools(include_disabled: bool = True):
    ...

def get_enabled_tools():
    ...

def get_all_tools():
    # Compatibility alias for old imports
    return list_tools(include_disabled=True)
```

Important compatibility rule:

```text
Keep get_all_tools() as alias to avoid old MCP import crash.
```

Suggested runtime type:

```python
from dataclasses import dataclass
from typing import Callable
from app.tools.schemas import ToolSpec


@dataclass
class RegisteredTool:
    spec: ToolSpec
    executor: Callable
```

Registry behavior:

```text
- Tool names must be unique.
- Disabled tools must not execute.
- Unimplemented tools must not execute.
- Approval-required/destructive tools must not execute in Fix 5.
- list_tools can show disabled/planned tools.
- get_enabled_tools should return only safe executable tools.
```

---

## 7. Required vCenter tools

Create or improve:

```text
apps/engine/app/tools/vcenter_tools.py
```

Required tools:

```text
1. list_vms
2. get_vm_details
3. list_hosts
4. list_datastores
```

### 7.1 `list_vms`

Backend endpoint:

```http
GET /api/v1/inventory/vms
```

Tool input:

```json
{"refresh": false}
```

Expected normalized output:

```json
{
  "ok": true,
  "tool": "list_vms",
  "count": 286,
  "cached": false,
  "items": [
    {
      "name": "roshellevm02",
      "power_state": "poweredOff",
      "cpu": 2,
      "memory_gb": 8,
      "ip_address": null,
      "host": "esxi01.dclab.com",
      "datastore": "datastore01"
    }
  ]
}
```

### 7.2 `get_vm_details`

Backend endpoint:

```http
GET /api/v1/context/vm-details?name=<vm_name>
```

Tool input:

```json
{"vm_name": "roshellevm02", "refresh": false}
```

Expected normalized output:

```json
{
  "ok": true,
  "tool": "get_vm_details",
  "data": {
    "name": "roshellevm02",
    "power_state": "poweredOff",
    "host": "esxi01.dclab.com",
    "datastore": "datastore01",
    "ip_address": null,
    "guest_os": "Red Hat Enterprise Linux 8 (64-bit)",
    "cpu": 2,
    "memory_gb": 8,
    "tools_status": "toolsNotRunning"
  }
}
```

If not found:

```json
{
  "ok": false,
  "tool": "get_vm_details",
  "error_code": "VM_NOT_FOUND",
  "message": "No VM named roshellevm02 was found."
}
```

Never return fake empty data like:

```text
Power State: unknown
CPU: 0
Memory: 0 GB
N/A everywhere
```

### 7.3 `list_hosts`

Backend endpoint:

```http
GET /api/v1/inventory/hosts
```

Tool input:

```json
{"refresh": false}
```

Expected normalized output:

```json
{
  "ok": true,
  "tool": "list_hosts",
  "count": 2,
  "items": [
    {
      "name": "esxi01.dclab.com",
      "connection_state": "connected",
      "power_state": "poweredOn",
      "cpu_cores": 32,
      "cpu_threads": 64,
      "memory_gb": 256,
      "vm_count": 120,
      "version": "7.0.3",
      "cluster": "Core-Cluster"
    }
  ]
}
```

### 7.4 `list_datastores`

Backend endpoint:

```http
GET /api/v1/inventory/datastores
```

Tool input:

```json
{"refresh": false}
```

Expected normalized output:

```json
{
  "ok": true,
  "tool": "list_datastores",
  "count": 25,
  "items": [
    {
      "name": "datastore01",
      "type": "VMFS",
      "capacity_gb": 1024,
      "free_gb": 200,
      "used_gb": 824,
      "used_percent": 80,
      "accessible": true
    }
  ]
}
```

---

## 8. Backend API client for tools

Agent Engine should call FastAPI internal service, not vCenter directly.

Recommended environment variable:

```env
FASTAPI_INTERNAL_BASE_URL=http://fastapi.agentic-app.svc.cluster.local:8000
```

Create helper:

```text
apps/engine/app/tools/http_client.py
```

Required behavior:

```text
- Use internal FastAPI URL.
- Timeout every tool call.
- Parse JSON.
- If HTTP status is non-2xx, return ok=false.
- Do not log credentials.
- Include request ID/run ID if available.
```

Example helper:

```python
import os
import httpx

FASTAPI_BASE_URL = os.getenv(
    "FASTAPI_INTERNAL_BASE_URL",
    "http://fastapi.agentic-app.svc.cluster.local:8000",
)


async def call_backend_get(path: str, params: dict | None = None) -> dict:
    url = f"{FASTAPI_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)

    try:
        data = resp.json()
    except Exception:
        return {
            "ok": False,
            "error_code": "BACKEND_INVALID_RESPONSE",
            "message": resp.text[:300],
        }

    if resp.status_code >= 400:
        return {
            "ok": False,
            "error_code": data.get("error_code", "BACKEND_ERROR"),
            "message": data.get("message", data.get("detail", "Backend request failed")),
            "status_code": resp.status_code,
        }

    return data
```

---

## 9. Tool result cache with Redis

Create:

```text
apps/engine/app/tools/cache.py
```

Purpose:

```text
Cache successful read-only tool results to reduce repeated calls to FastAPI/vCenter.
```

Environment variables:

```env
REDIS_URL=redis://redis.agentic-app.svc.cluster.local:6379/0
TOOL_CACHE_ENABLED=true
```

### Cache key design

```text
tool:{tool_name}:{hash(args)}
```

Example:

```text
tool:get_vm_details:83d91b...
tool:list_vms:de19ab...
```

Hash implementation:

```python
import hashlib
import json


def make_cache_key(tool_name: str, args: dict) -> str:
    normalized = json.dumps(args or {}, sort_keys=True, default=str)
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"tool:{tool_name}:{digest}"
```

### Cache TTLs

```text
list_vms:           30 seconds
get_vm_details:     30 seconds
list_hosts:         60 seconds
list_datastores:    60 seconds
```

### Cache bypass

Tool input should support:

```json
{"refresh": true}
```

If `refresh=true`:

```text
- skip reading cache
- call backend
- replace cache only if success
```

### Safe cache rules

Cache only if all are true:

```text
✅ tool risk_level == read_only
✅ result ok == true
✅ result does not contain error_code
✅ HTTP/tool status is success
✅ result does not contain authentication/session error text
```

Never cache if result contains:

```text
NotAuthenticated
session is not authenticated
VCENTER_AUTH_FAILED
VCENTER_SESSION_EXPIRED
VCENTER_NOT_CONFIGURED
VCENTER_UNREACHABLE
NoPermission
invalid login
```

---

## 10. Tool execution wrapper

Create or update:

```text
apps/engine/app/tools/executor.py
```

Required behavior:

```text
1. Get tool by name.
2. Check tool exists.
3. Check enabled.
4. Check implemented.
5. Check risk level.
6. Block non-read-only tools in Fix 5.
7. Check Redis cache.
8. Execute tool.
9. Cache successful result.
10. Return normalized tool result.
```

Pseudo-code:

```python
async def execute_tool(name: str, args: dict, *, run_id: str | None = None) -> dict:
    registered = get_tool(name)
    if not registered:
        return {"ok": False, "error_code": "TOOL_NOT_FOUND", "tool": name}

    spec = registered.spec

    if not spec.enabled or not spec.implemented:
        return {
            "ok": False,
            "error_code": "TOOL_DISABLED",
            "tool": name,
            "message": f"{name} is not enabled in this phase.",
        }

    if spec.risk_level != RiskLevel.READ_ONLY:
        return {
            "ok": False,
            "error_code": "TOOL_REQUIRES_APPROVAL",
            "tool": name,
            "message": f"{name} requires approval and is disabled in Fix 5.",
        }

    refresh = bool(args.pop("refresh", False))

    if not refresh:
        cached = await tool_cache.get(name, args)
        if cached:
            cached["cached"] = True
            return cached

    result = await registered.executor(args)
    normalized = normalize_tool_result(name, result)

    if should_cache(spec, normalized):
        await tool_cache.set(name, args, normalized, ttl=spec.cache_ttl_seconds)

    normalized["cached"] = False
    return normalized
```

---

## 11. Tool trace events

Tool execution should emit clear tool trace events to the SSE stream.

Required events:

```text
tool_call
tool_result
tool_cache_hit
tool_error
```

Example:

```text
event: tool_call
data: {"tool":"get_vm_details","args":{"vm_name":"roshellevm02"},"risk":"read_only"}

event: tool_result
data: {"tool":"get_vm_details","status":"success","summary":"Found VM roshellevm02, poweredOff"}

event: tool_cache_hit
data: {"tool":"get_vm_details","cache_key":"tool:get_vm_details:83d91b..."}
```

If blocked:

```text
event: tool_error
data: {"tool":"power_on_vm","error_code":"TOOL_REQUIRES_APPROVAL","message":"power_on_vm requires approval and is disabled in Fix 5."}
```

---

## 12. Integration with graph nodes

Update:

```text
apps/engine/app/graph/nodes.py
```

The `execute_tools` node should use the new registry executor.

Correct:

```text
graph node → execute_tool() → registry → vCenter tool executor → FastAPI
```

Wrong:

```text
graph node → httpx directly to /api/v1/context/vm-details
```

---

## 13. Tool selection examples

The classifier/router should map:

```text
"list all VMs"                     → list_vms
"show powered off VMs"             → list_vms first or get_powered_off_vms if already available
"inspect roshellevm02"             → get_vm_details {"vm_name":"roshellevm02"}
"show details for roshellevm02"    → get_vm_details {"vm_name":"roshellevm02"}
"list hosts"                       → list_hosts
"show all ESXi hosts"              → list_hosts
"list datastores"                  → list_datastores
"which datastores are full"        → list_datastores for Fix 5
```

---

## 14. Validation tests

### 14.1 Registry tests

Create tests for:

```text
- ToolSpec can be created.
- RiskLevel enum has read_only, low_risk, approval_required, destructive.
- Registry contains list_vms.
- Registry contains get_vm_details.
- Registry contains list_hosts.
- Registry contains list_datastores.
- get_enabled_tools returns only enabled implemented tools.
- get_all_tools compatibility alias works.
```

Example:

```python
def test_registry_contains_core_tools():
    names = [t.name for t in get_enabled_tools()]
    assert "list_vms" in names
    assert "get_vm_details" in names
    assert "list_hosts" in names
    assert "list_datastores" in names
```

### 14.2 Risk tests

If you add placeholder `power_on_vm`:

```python
async def test_power_on_blocked():
    result = await execute_tool("power_on_vm", {"vm_name": "test"})
    assert result["ok"] is False
    assert result["error_code"] == "TOOL_REQUIRES_APPROVAL"
```

### 14.3 Tool execution tests

Mock FastAPI responses:

```text
list_vms → returns VM list
get_vm_details → returns one VM
list_hosts → returns hosts
list_datastores → returns datastores
```

Assertions:

```text
- Tool returns ok=true
- Tool name is correct
- Count is correct
- cached=false on first call
```

### 14.4 Cache tests

Test:

```text
1. First call executes backend and stores result.
2. Second call returns cached=true.
3. refresh=true bypasses cache.
4. ok=false result is not cached.
5. NotAuthenticated result is not cached.
6. VCENTER_SESSION_EXPIRED result is not cached.
```

Example:

```python
async def test_auth_failure_not_cached():
    result = {
        "ok": False,
        "error_code": "VCENTER_SESSION_EXPIRED",
        "message": "session is not authenticated",
    }
    assert should_cache(tool_spec, result) is False
```

### 14.5 Chat integration tests

Use prompts:

```text
list all VMs
inspect roshellevm02
list hosts
list datastores
```

Expected tool calls:

```text
list all VMs          → list_vms
inspect roshellevm02  → get_vm_details
list hosts            → list_hosts
list datastores       → list_datastores
```

Blocked action prompt:

```text
power on roshellevm02
```

Expected:

```text
No tool execution.
Blocked or TOOL_REQUIRES_APPROVAL.
```

---

## 15. Manual verification commands

### 15.1 Check Agent Engine tools

```powershell
curl.exe -k https://api.dclab.local/api/v1/tools
```

Expected tools:

```text
list_vms
get_vm_details
list_hosts
list_datastores
```

Each should include:

```text
risk_level: read_only
enabled: true
implemented: true
requires_approval: false
```

### 15.2 Test chat stream: list VMs

```powershell
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"list all VMs","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' `
  https://api.dclab.local/api/v1/chat/stream
```

Expected SSE:

```text
tool_call list_vms
tool_result list_vms success
final answer with VM summary
done
```

### 15.3 Test chat stream: VM details

```powershell
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"inspect roshellevm02","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' `
  https://api.dclab.local/api/v1/chat/stream
```

Expected:

```text
intent get_vm_details
tool_call get_vm_details {"vm_name":"roshellevm02"}
tool_result get_vm_details success
final answer includes power state, host, datastore, IP
```

### 15.4 Test cache behavior

Run same prompt twice:

```text
inspect roshellevm02
```

Expected first run:

```text
cached=false
```

Expected second run:

```text
cached=true or tool_cache_hit event
```

Then run with refresh if supported:

```json
{"message": "inspect roshellevm02", "refresh": true}
```

Expected:

```text
cached=false
```

### 15.5 Test no bad auth cache

Force or simulate an auth failure.

Expected:

```text
- error is not cached
- retry happens once
- next valid call does not replay old auth failure
```

Search logs:

```powershell
kubectl -n agentic-app logs deployment/agent-engine --tail=100 | Select-String "VCENTER_SESSION_EXPIRED"
kubectl -n agentic-app logs deployment/agent-engine --tail=100 | Select-String "cache"
```

Expected:

```text
No cached auth failure replay.
```

---

## 16. Acceptance checklist

Fix 5 is complete when:

```text
[ ] ToolSpec exists
[ ] RiskLevel enum exists
[ ] Tool registry exists
[ ] get_all_tools compatibility alias exists
[ ] list_vms tool registered
[ ] get_vm_details tool registered
[ ] list_hosts tool registered
[ ] list_datastores tool registered
[ ] Tools have category metadata
[ ] Tools have risk metadata
[ ] Non-read-only tools are blocked
[ ] Tool executor uses registry
[ ] Graph execute_tools node uses registry executor
[ ] Tool result cache uses Redis
[ ] Successful read-only results are cached
[ ] Failed/auth results are not cached
[ ] refresh=true bypasses cache
[ ] /api/v1/tools returns registered tools
[ ] Chat prompt “list all VMs” calls list_vms
[ ] Chat prompt “inspect roshellevm02” calls get_vm_details
[ ] Chat prompt “list hosts” calls list_hosts
[ ] Chat prompt “list datastores” calls list_datastores
[ ] Tool trace shows tool_call/tool_result/cache_hit
[ ] No dangerous vCenter actions execute
[ ] CI/CD passes
[ ] Argo CD syncs successfully
```

---

## 17. Codex prompt for Fix 5

Use this prompt:

```text
You are working in my new Kubernetes/RKE2 vCenter Agentic Ops Platform.

Implement Fix 5: vCenter tools in the Agent Engine.

Current context:
- Phase 1.1 dashboard shell is complete.
- Phase 1.2 credentials are stored in Kubernetes Secret.
- Phase 1.3 real vCenter inventory/context APIs are complete.
- Phase 1.4 fixes are being applied step-by-step.
- Fix 2 adds persistent VCenterSession.
- Fix 3 fixes host-vs-VM classifier routing.
- Fix 4 replaces hardcoded formatter with LLM answer generation.
- Now Fix 5 must build the real vCenter tool layer inside the Agent Engine.

Focus areas:
1. Tool registry with ToolSpec.
2. RiskLevel enum.
3. list_vms tool.
4. get_vm_details tool.
5. list_hosts tool.
6. list_datastores tool.
7. Redis-backed tool result cache.

Requirements:
1. Create or update apps/engine/app/tools/schemas.py.
2. Add RiskLevel enum:
   - read_only
   - low_risk
   - approval_required
   - destructive
3. Add ToolCategory enum or equivalent category field.
4. Add ToolSpec model with:
   - name
   - display_name
   - description
   - category
   - risk_level
   - enabled
   - implemented
   - requires_approval
   - cache_ttl_seconds
   - backend_endpoint
   - input_schema
5. Create or update apps/engine/app/tools/registry.py.
6. Add:
   - register_tool
   - get_tool
   - list_tools
   - get_enabled_tools
   - get_all_tools compatibility alias
   - execute_tool
7. Create or update apps/engine/app/tools/vcenter_tools.py.
8. Register read-only tools:
   - list_vms
   - get_vm_details
   - list_hosts
   - list_datastores
9. Tools must call FastAPI internal backend, not vCenter directly:
   FASTAPI_INTERNAL_BASE_URL=http://fastapi.agentic-app.svc.cluster.local:8000
10. Use endpoints:
   - list_vms → GET /api/v1/inventory/vms
   - get_vm_details → GET /api/v1/context/vm-details?name=<vm_name>
   - list_hosts → GET /api/v1/inventory/hosts
   - list_datastores → GET /api/v1/inventory/datastores
11. Add Redis tool-result cache in apps/engine/app/tools/cache.py.
12. Use REDIS_URL env var.
13. Cache only successful read-only results.
14. Never cache failed/auth/session errors.
15. Never cache responses with:
   - NotAuthenticated
   - session is not authenticated
   - VCENTER_AUTH_FAILED
   - VCENTER_SESSION_EXPIRED
   - VCENTER_NOT_CONFIGURED
   - VCENTER_UNREACHABLE
   - NoPermission
   - invalid login
16. Support refresh=true to bypass cache.
17. Update graph execute_tools node to use execute_tool from registry.
18. Emit SSE/tool trace events:
   - tool_call
   - tool_result
   - tool_cache_hit
   - tool_error
19. Make sure non-read-only tools are blocked in this phase.
20. Do not implement power/delete/migrate/snapshot actions.
21. Update /api/v1/tools to return registry tools.
22. Add tests for:
   - ToolSpec
   - RiskLevel
   - registry contains core tools
   - get_all_tools alias
   - read-only tools execute
   - non-read-only tools blocked
   - Redis cache hit
   - refresh bypass
   - auth failure not cached
23. Validate with prompts:
   - list all VMs
   - inspect roshellevm02
   - list hosts
   - list datastores
   - power on roshellevm02
24. Expected:
   - read-only prompts call correct tools
   - risky prompt is blocked
   - tool trace shows correct events
   - no dangerous vCenter action executes

After coding, provide summary:
- files changed
- tools registered
- cache behavior
- tests run
- validation results
- remaining limitations
```

---

## 18. Final recommendation

Implement Fix 5 only after Fix 2 and Fix 3 are working.

Best order:

```text
1. Fix 2 — Persistent vCenter session
2. Fix 3 — Host vs VM classifier
3. Fix 4 — LLM answer generation
4. Fix 5 — Agent tool registry + vCenter tools + Redis cache
```

Why:

```text
Fix 5 tools depend on stable backend session and correct routing.
If Fix 2 and Fix 3 are broken, the new tool registry will still call bad backend behavior.
```
