markdown

# Fix 2 — vCenter Persistent Session

## What this fixes

Three compounding issues that cause `NotAuthenticated` on every tool call
after the first:

| # | Issue | File |
|---|---|---|
| 1 | `with_vcenter()` creates a new `SmartConnect` per call — sessions expire | `vcenter_client_factory.py` |
| 2 | No `host-details` endpoint — `get_host_details` silently calls VM endpoint | `context.py` + `mcp/server.py` |
| 3 | On auth failure there is no reconnect — error is returned immediately | `vcenter_client_factory.py` |

---

## Why `with_vcenter()` breaks

```
Request 1: with_vcenter(list_vms)
  → SmartConnect()   ← creates session A
  → list_vms runs
  → Disconnect()     ← destroys session A

Request 2: with_vcenter(list_hosts)
  → SmartConnect()   ← creates session B (new TCP + SSL handshake every time)
  → list_hosts runs
  → Disconnect()

Request N (after idle): with_vcenter(get_host_details)
  → SmartConnect()   ← may fail if vCenter throttles rapid connects
  → OR session object held elsewhere is stale → NotAuthenticated
```

pyVmomi sessions have a server-side idle timeout (default 30 minutes in
vCenter, but can be as low as 5 minutes in some configs). More critically,
creating a new SmartConnect for every request is expensive — each call does
a full TCP + SSL handshake + SOAP login. Under load this causes delays and
vCenter may rate-limit the login attempts.

The fix: one persistent `ServiceInstance` singleton. Before every call,
check the session is still alive. If dead, reconnect once and retry.

---

## Fix 1 — Replace `with_vcenter()` with `VCenterSession` singleton

### Full replacement for `apps/backend/app/services/vcenter_client_factory.py`

Replace the entire file with this:

```python
# apps/backend/app/services/vcenter_client_factory.py
"""
Persistent vCenter session singleton.

Replaces the old with_vcenter() per-request connection pattern.
One ServiceInstance is kept alive for the lifetime of the FastAPI pod.
Before every call, the session is validated. On NotAuthenticated,
the session is re-established and the call is retried exactly once.
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

import structlog
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim, vmodl

from app.core.inventory_errors import error_response
from app.services.k8s_secret_store import VCENTER_SECRET_NAME, get_secret

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=4)
T = TypeVar("T")


# ── Credential loader ─────────────────────────────────────────────────────────


def get_vcenter_credentials() -> dict | None:
    s = get_secret(VCENTER_SECRET_NAME)
    if not s:
        return None
    url  = s.get("VCENTER_URL", "")
    user = s.get("VCENTER_USERNAME", "")
    pwd  = s.get("VCENTER_PASSWORD", "")
    ssl  = s.get("VCENTER_VERIFY_SSL", "false") == "true"
    if not url or not user or not pwd:
        return None
    return {"url": url, "username": user, "password": pwd, "verify_ssl": ssl}


def _parse_host_port(url: str) -> tuple[str, int]:
    host = url.replace("https://", "").replace("http://", "").split("/")[0]
    port = 443
    if ":" in host:
        host, port_str = host.split(":", 1)
        port = int(port_str)
    return host, port


# ── Singleton session ─────────────────────────────────────────────────────────


class VCenterSession:
    """
    Thread-safe singleton holding one persistent pyVmomi ServiceInstance.

    Usage:
        result = vcenter_session.run(lambda si, content: list_vms(si, content))

    The session is created lazily on the first call and kept alive between
    calls. If the session expires or vCenter restarts, it is automatically
    re-established and the call is retried once.
    """

    def __init__(self) -> None:
        self._si: vim.ServiceInstance | None = None
        self._content: vim.ServiceContent | None = None
        self._creds: dict | None = None
        self._lock = threading.Lock()

    # ── Internal: connection management ──────────────────────────────────────

    def _do_connect(self, creds: dict) -> None:
        """Establish a new ServiceInstance. Caller must hold self._lock."""
        host, port = _parse_host_port(creds["url"])
        logger.info("vcenter_connecting", host=host)
        si = SmartConnect(
            host=host,
            user=creds["username"],
            pwd=creds["password"],
            port=port,
            disableSslCertValidation=not creds["verify_ssl"],
        )
        self._si = si
        self._content = si.RetrieveContent()
        self._creds = creds
        logger.info("vcenter_connected", host=host)

    def _disconnect_quiet(self) -> None:
        """Disconnect without raising. Used before reconnect."""
        try:
            if self._si is not None:
                Disconnect(self._si)
        except Exception:
            pass
        finally:
            self._si = None
            self._content = None

    def _is_alive(self) -> bool:
        """
        Ping the session manager to check the session is still valid.
        Returns False on any error — caller will reconnect.
        """
        try:
            session = self._si.content.sessionManager.currentSession  # type: ignore[union-attr]
            return session is not None
        except Exception:
            return False

    def _ensure_connected(self) -> dict | None:
        """
        Ensure there is a live session. Returns error_response dict on
        failure, None on success. Caller must hold self._lock.
        """
        creds = get_vcenter_credentials()
        if not creds:
            return error_response("VCENTER_NOT_CONFIGURED")

        # Already connected and alive — nothing to do
        if self._si is not None and self._is_alive():
            return None

        # Session is dead or never started — (re)connect
        self._disconnect_quiet()
        try:
            self._do_connect(creds)
            return None
        except Exception as exc:
            msg = str(exc).lower()
            logger.warning("vcenter_connect_failed", error=str(exc)[:120])
            if "auth" in msg or "login" in msg or "password" in msg:
                return error_response("VCENTER_AUTH_FAILED")
            if "refused" in msg or "timeout" in msg or "unreachable" in msg:
                return error_response("VCENTER_UNREACHABLE")
            if "ssl" in msg or "certificate" in msg:
                return error_response("VCENTER_SSL_ERROR")
            return error_response("VCENTER_INVENTORY_ERROR")

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, fn: Callable[[vim.ServiceInstance, vim.ServiceContent], T]) -> T | dict:
        """
        Run fn(si, content) with a live session.

        On NotAuthenticated:
          1. Clear session
          2. Reconnect
          3. Retry fn once

        Returns error_response dict on unrecoverable failure.
        """
        with self._lock:
            err = self._ensure_connected()
            if err:
                return err

            try:
                return fn(self._si, self._content)  # type: ignore[arg-type]

            except (vim.fault.NotAuthenticated, vmodl.fault.SystemError) as exc:
                # Session expired mid-call — reconnect and retry once
                logger.warning(
                    "vcenter_session_expired_retrying",
                    error=type(exc).__name__,
                )
                self._disconnect_quiet()
                retry_err = self._ensure_connected()
                if retry_err:
                    return retry_err
                try:
                    return fn(self._si, self._content)  # type: ignore[arg-type]
                except Exception as retry_exc:
                    logger.error("vcenter_retry_failed", error=str(retry_exc)[:120])
                    return error_response("VCENTER_SESSION_EXPIRED")

            except Exception as exc:
                msg = str(exc).lower()
                logger.error("vcenter_call_failed", error=str(exc)[:120])
                if "auth" in msg or "login" in msg:
                    return error_response("VCENTER_AUTH_FAILED")
                if "refused" in msg or "timeout" in msg:
                    return error_response("VCENTER_UNREACHABLE")
                return error_response("VCENTER_INVENTORY_ERROR")

    def force_reconnect(self) -> dict | None:
        """
        Force a fresh connection regardless of current session state.
        Used by the connect_vcenter tool and the Settings test endpoint.
        Returns error_response on failure, None on success.
        """
        with self._lock:
            logger.info("vcenter_force_reconnect")
            self._disconnect_quiet()
            return self._ensure_connected()

    def status(self) -> dict:
        """Return connection status for /health and monitoring endpoints."""
        with self._lock:
            if self._si is None:
                return {"connected": False, "reason": "no_session"}
            alive = self._is_alive()
            return {
                "connected": alive,
                "host": self._creds["url"] if self._creds else None,
                "reason": "ok" if alive else "session_expired",
            }


# ── Module-level singleton ────────────────────────────────────────────────────

vcenter_session = VCenterSession()


# ── Backwards-compatible helpers ──────────────────────────────────────────────
# Keep these so existing callers (inventory.py, context.py) work without
# changing every call site immediately.


def with_vcenter(fn: Callable) -> Any:
    """
    Backwards-compatible wrapper.
    Old code: with_vcenter(list_vms)
    New code: vcenter_session.run(list_vms)   ← preferred going forward
    Both work. Migrate call sites to vcenter_session.run() over time.
    """
    return vcenter_session.run(fn)


async def async_with_vcenter(fn: Callable) -> Any:
    """
    Async wrapper — runs pyVmomi (synchronous) in the thread executor
    so it does not block the FastAPI event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, vcenter_session.run, fn)


def connect_to_vcenter(creds: dict):
    """
    Backwards-compatible. Forces a fresh connection with given creds.
    Used by vcenter_connection_service.py test endpoint.
    """
    from pyVim.connect import SmartConnect as _SC
    host, port = _parse_host_port(creds["url"])
    return _SC(
        host=host,
        user=creds["username"],
        pwd=creds["password"],
        port=port,
        disableSslCertValidation=not creds["verify_ssl"],
    )


def disconnect_from_vcenter(si) -> None:
    try:
        Disconnect(si)
    except Exception:
        pass
```

---

## Fix 2 — Add `host-details` endpoint to `context.py`

### The bug

In `apps/mcp/server.py` the endpoint map has:

```python
"get_host_details": "/api/v1/context/vm-details",   # ← WRONG
```

`/api/v1/context/vm-details` searches the VM list by name. When you ask for
`esxi01.dclab.com` it searches VMs, finds nothing (it's a host not a VM),
and returns an empty table with all `N/A` values.

### Step A — Add `host-details` endpoint in `apps/backend/app/api/routes/context.py`

Add this function to the file. Insert it after the `vm_details` endpoint
(around line 90):

```python
@router.get("/host-details")
async def host_details(name: str = Query(..., min_length=1)):
    """
    Get details for a single ESXi host by name or partial match.
    Accepts: esxi01, esxi01.dclab.com, esx-01, etc.
    """
    def _fetch(si, content):
        from app.services.vcenter_inventory_service import list_hosts
        hosts = list_hosts(si, content)
        lower = name.lower()

        # Try exact match first, then partial
        matches = [h for h in hosts if lower in h["name"].lower()]
        if not matches:
            return {
                "hosts": [],
                "count": 0,
                "error": f"Host '{name}' not found. Available hosts: "
                         + ", ".join(h["name"] for h in hosts[:5]),
            }
        exact = [h for h in matches if h["name"].lower() == lower]
        result = exact[0] if exact else matches[0]
        return {
            "hosts": [result],
            "count": 1,
            "summary": (
                f"Host {result['name']} — "
                f"{result.get('connection_state', 'unknown')} — "
                f"{result.get('vm_count', 0)} VMs — "
                f"vSphere {result.get('version', 'unknown')}"
            ),
        }

    result = with_vcenter(_fetch)
    if isinstance(result, dict) and "error_code" in result:
        return JSONResponse(result, status_code=409)

    data = {**result, "source": "vcenter", "cached": False, "collected_at": _now()}
    return JSONResponse(data)
```

### Step B — Fix the endpoint map in `apps/mcp/server.py`

Find the `endpoint_map` dict in `_dispatch()` (around line 95) and change:

```python
# BEFORE (wrong — searches VMs for a host name)
"get_host_details": "/api/v1/context/vm-details",

# AFTER (correct — dedicated host search endpoint)
"get_host_details": "/api/v1/context/host-details",
```

Also fix the args forwarding in `_dispatch()`. After the endpoint_map,
find the block that sets `params` and add a case for `host_details`:

```python
# BEFORE — only handles get_vm_details
params = {}
if tool.name == "get_vm_details" and args.get("name"):
    params["name"] = args["name"]

# AFTER — handles both vm and host detail lookups
params = {}
if tool.name == "get_vm_details" and args.get("name"):
    params["name"] = args["name"]
elif tool.name == "get_host_details" and args.get("host_name"):
    params["name"] = args["host_name"]   # endpoint uses ?name= for both
elif tool.name == "get_host_details" and args.get("name"):
    params["name"] = args["name"]        # fallback if agent passes "name"
```

---

## Fix 3 — Expose `connect_vcenter` as a force-reconnect tool

The agent already calls `connect_vcenter` as a tool when it detects auth
failure (as seen in the log: `Turn 2: connect_vcenter → "Already connected"`).
The old response was misleading. Wire it to `force_reconnect()` instead.

### Add to `apps/backend/app/api/routes/connections.py`

Find the existing `connect_vcenter` endpoint and update it:

```python
@router.post("/vcenter/reconnect")
async def vcenter_reconnect():
    """
    Force a fresh vCenter session regardless of current state.
    Called by: agent connect_vcenter tool, Settings UI test button.
    """
    from app.services.vcenter_client_factory import vcenter_session
    err = vcenter_session.force_reconnect()
    if err:
        return JSONResponse(err, status_code=409)
    status = vcenter_session.status()
    return JSONResponse({
        "ok": True,
        "message": f"Connected to {status.get('host', 'vCenter')}",
        "status": status,
    })


@router.get("/vcenter/status")
async def vcenter_status():
    """Return current session liveness without triggering a reconnect."""
    from app.services.vcenter_client_factory import vcenter_session
    return JSONResponse(vcenter_session.status())
```

### Update MCP endpoint map to call reconnect endpoint

In `apps/mcp/server.py` `endpoint_map`, change the `connect_vcenter` entry:

```python
# BEFORE — no such endpoint existed
"connect_vcenter": "/api/v1/connections/connect",

# AFTER
"connect_vcenter": "/api/v1/connections/vcenter/reconnect",
```

And change the HTTP method in `_dispatch()`. Currently everything uses
`GET`. The reconnect endpoint is `POST`. Add a method override:

```python
# In _dispatch(), after endpoint_map is defined:
method_map: dict[str, str] = {
    "connect_vcenter": "POST",
}

# Then in the try block, replace:
resp = await client.get(url, params=params)

# With:
http_method = method_map.get(tool.name, "GET")
if http_method == "POST":
    resp = await client.post(url, json=args)
else:
    resp = await client.get(url, params=params)
```

---

## Summary of all file changes

| File | Change |
|---|---|
| `apps/backend/app/services/vcenter_client_factory.py` | Full replacement — `VCenterSession` singleton |
| `apps/backend/app/api/routes/context.py` | Add `GET /api/v1/context/host-details` |
| `apps/mcp/server.py` | Fix `get_host_details` endpoint + args + method map |
| `apps/backend/app/api/routes/connections.py` | Add `/vcenter/reconnect` and `/vcenter/status` |

No changes needed to `inventory.py` or `context.py` existing endpoints —
they all call `with_vcenter()` which now delegates to the singleton.

---

## Execution checklist

```
Step 1  Make the vcenter_client_factory.py replacement
Step 2  Add host-details endpoint to context.py
Step 3  Fix endpoint map + args in mcp/server.py
Step 4  Add /vcenter/reconnect to connections.py
Step 5  Local test (see below)
Step 6  git push → CI builds backend + mcp images
Step 7  Argo CD syncs agentic-app
Step 8  Run validation tests
```

---

## Local test before pushing

```python
# Quick unit test — paste into Python REPL or test file
# Set these env vars first:
# VCENTER_URL, VCENTER_USERNAME, VCENTER_PASSWORD in k8s secret
# or set get_vcenter_credentials() to return test creds

from app.services.vcenter_client_factory import vcenter_session
from app.services.vcenter_inventory_service import list_hosts

# Test 1: first connection
result = vcenter_session.run(list_hosts)
assert isinstance(result, list), f"Expected list, got: {result}"
print(f"Hosts found: {len(result)}")

# Test 2: session stays alive (no reconnect should happen)
result2 = vcenter_session.run(list_hosts)
assert isinstance(result2, list)
print("Session reuse: OK")

# Test 3: status check
status = vcenter_session.status()
assert status["connected"] is True
print(f"Status: {status}")

# Test 4: force reconnect
err = vcenter_session.force_reconnect()
assert err is None, f"Reconnect failed: {err}"
print("Force reconnect: OK")

# Test 5: find a host by name
def find_host(si, content):
    from app.services.vcenter_inventory_service import list_hosts as lh
    hosts = lh(si, content)
    lower = "esxi01".lower()
    matches = [h for h in hosts if lower in h["name"].lower()]
    return matches

hosts = vcenter_session.run(find_host)
print(f"esxi01 search result: {hosts}")
```

---

## Validation after deploy

```powershell
# 1. Confirm new FastAPI image deployed
kubectl -n agentic-app get pods -l app=fastapi -o jsonpath="{.items[0].spec.containers[0].image}"

# 2. Test host-details endpoint directly
$POD = kubectl -n agentic-app get pod -l app=fastapi -o jsonpath="{.items[0].metadata.name}"
kubectl -n agentic-app exec $POD -- curl -s `
  "http://localhost:8000/api/v1/context/host-details?name=esxi01"
# Expected:
# {"hosts":[{"id":"...","name":"esxi01.dclab.com","connection_state":"connected",...}],"count":1}

# 3. Test via agent chat stream
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"get details for esxi01.dclab.com","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' `
  https://api.dclab.local/api/v1/chat/stream

# Expected SSE sequence:
# data: {"type":"start",...}
# data: {"type":"intent","intent":"list_hosts","entity":"esxi01.dclab.com"}
#                                  ^^^^^^^^^^^ must be list_hosts, not get_vm_details
# data: {"type":"tool_call","tool":"get_host_details",...}
# data: {"type":"tool_result","tool":"get_host_details","status":"success","data_count":1}
# data: {"type":"final","content":"esxi01.dclab.com is connected, running N VMs..."}
# data: {"type":"done"}

# 4. Test force reconnect
curl.exe -k -X POST https://api.dclab.local/api/v1/connections/vcenter/reconnect
# Expected: {"ok":true,"message":"Connected to core-infra-vc01.dclab.com",...}

# 5. Test session persistence (two calls, no reconnect in between)
kubectl -n agentic-app logs deployment/fastapi --tail=20 | Select-String "vcenter_connect"
# Must show vcenter_connected once at startup
# Must NOT show vcenter_connecting on every request
# If you see vcenter_connecting on every request: singleton is not working
```

---

## What changes in agent behaviour after this fix

| Before | After |
|---|---|
| Every tool call creates new TCP+SSL+login | One connection held for pod lifetime |
| `NotAuthenticated` after idle period | Auto-reconnect + retry — transparent to agent |
| `connect_vcenter` tool returns "Already connected" but session still broken | `connect_vcenter` forces a genuine fresh session |
| `get details for esxi01.dclab.com` → empty VM table (N/A everywhere) | `get details for esxi01.dclab.com` → real host data |
| Agent burns 4+ turns on auth error retry loop | Session established once, all turns used for real work |

---

## What is NOT fixed in Phase 2

| Issue | Phase |
|---|---|
| Intent classifier still routes ESXi names to `get_vm_details` | Phase 3 |
| `generate_answer_node` uses hardcoded formatting | Phase 4 |
| govc `multiple instances` error | Phase 6 |

After Phase 2 the session will be live and `host-details` endpoint will
exist. But the agent's intent classifier still routes
`"get details for esxi01.dclab.com"` to `get_vm_details` intent which
calls `/api/v1/context/vm-details` not the new `/api/v1/context/host-details`.
Phase 3 fixes the classifier routing.
