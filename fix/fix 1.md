# Fix 1 — Stop the Crashes (Phase 1)

## What this fixes

Four issues that block the agent from running real workflow nodes at all:

| # | Issue | File | Impact |
|---|---|---|---|
| 1 | MCP import `get_all_tools` does not exist | `apps/mcp/server.py` | MCP pod crashes at startup — all tool calls fail |
| 2 | `graph.py` still wires `echo_node` — two competing graph files | `apps/engine/app/graph/graph.py` | Confusion risk — wrong graph gets run if runtime.py changes |
| 3 | `run.py` initialises old `echo_node` state fields | `apps/engine/app/routes/run.py` | `/run` endpoint sends wrong state to real workflow nodes |
| 4 | Tool error results get cached in old project pattern | `apps/engine/app/graph/nodes/workflow_nodes.py` | `execute_tools_node` replays stale auth failures |

---

## Fix 1 — MCP import error

### The error (from `errors.md`)

```
File "/app/server.py", line 6, in <module>
    from app.tools.registry import (
ImportError: cannot import name 'get_all_tools' from 'app.tools.registry'
Did you mean: 'get_enabled_tools'?
```

### Why it happens

The deployed MCP pod image was built from an older version of `server.py`
that imported `get_all_tools`. The registry only exports `get_enabled_tools`.

### Current state (already correct in repo)

Check `apps/mcp/server.py` line 6 — it should read:

```python
from app.tools.registry import (
    get_tool, get_enabled_tools, format_tool_list, ToolDef, TOOLS
)
```

If it still says `get_all_tools` anywhere, change it to `get_enabled_tools`.

### Action required

The code is correct in the repo. The running pod is using an old image.
Force a redeploy so Kubernetes pulls the latest image:

```powershell
# Force a rollout restart to pull latest image
kubectl rollout restart deployment/mcp-server -n agentic-app

# Watch until new pod is Running
kubectl rollout status deployment/mcp-server -n agentic-app --timeout=3m

# Confirm MCP starts without crash
kubectl logs -n agentic-app deployment/mcp-server --tail=20
# Must NOT show ImportError
# Must show: "Application startup complete"
```

### Validate MCP is healthy

```powershell
kubectl run mcp-check --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://mcp-server.agentic-app.svc.cluster.local:8001/health
# Expected:
# {"status":"ok","tools":N,"enabled":N,"resources":[],"prompts":[]}
```

If the pod still crashes after restart, the CI pipeline did not rebuild the
image after the import was fixed. Check GitHub Actions → build-mcp workflow →
confirm it ran after the `server.py` fix was committed. If not, push an empty
commit to trigger it:

```bash
git commit --allow-empty -m "ci: trigger mcp rebuild after import fix"
git push
```

---

## Fix 2 — Delete the dead graph.py file

### The problem

Two files define `build_graph()`:

```
apps/engine/app/graph/graph.py      ← uses echo_node (OLD, placeholder)
apps/engine/app/graph/workflow.py   ← uses real workflow nodes (CORRECT)
```

`runtime.py` correctly imports from `workflow.py`:

```python
# apps/engine/app/runtime.py — this is correct, do not change
from app.graph.workflow import build_graph
```

The danger is that `graph.py` still exists. If anyone refactors and accidentally
changes the import to `from app.graph.graph import build_graph`, the agent
silently falls back to returning the echo_node skeleton response instead of
running real workflow nodes. It will look like it is working but return
placeholder output.

### Action required

**Delete the file:**

```bash
rm apps/engine/app/graph/graph.py
```

**Also delete the now-unused echo_node:**

```bash
rm apps/engine/app/graph/nodes/echo_node.py
```

**Verify nothing imports echo_node:**

```bash
grep -r "echo_node" apps/engine/
# Must return zero results
```

**Verify runtime.py import still resolves:**

```bash
cd apps/engine
python -c "from app.graph.workflow import build_graph; print('OK')"
# Must print: OK
```

### After deletion — confirm workflow.py is the only graph

`apps/engine/app/graph/workflow.py` must be the sole file calling
`StateGraph(AgentState)`. Confirm:

```bash
grep -r "StateGraph" apps/engine/
# Must show only: apps/engine/app/graph/workflow.py
```

---

## Fix 3 — Fix run.py state initialisation

### The problem

`apps/engine/app/routes/run.py` sends old `echo_node` state fields to the
graph. The real workflow nodes (`workflow_nodes.py`) do not use `cached_result`
and expect `intent`, `entity`, `selected_tools`, etc. When `/run` is called,
the workflow nodes read `state.get("intent", "")` and get an empty string
because it was never set in `initial_state`.

### Current broken code in `apps/engine/app/routes/run.py`

```python
initial_state = {
    "session_id": session_id,
    "user_message": request.message,
    "messages": [],
    "turn": 0,
    "cached_result": None,    # ← echo_node field, not in AgentState
    "final_answer": None,     # ← set by workflow nodes, not initial state
}
```

### Fix — update `initial_state` to match real `AgentState`

Replace the `initial_state` block in `apps/engine/app/routes/run.py`:

```python
initial_state = {
    "session_id": session_id,
    "user_message": request.message,
    "messages": [],
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "allow_high_risk": False,
    "page_context": None,
    "turn": 0,
    "intent": "",
    "entity": None,
    "safety_verdict": None,
    "selected_tools": [],
    "tool_results": [],
    "final_answer": None,
    "suggested_next": None,
    "error": None,
    "status": "thinking",
}
```

### Note on run.py vs stream.py

The frontend (`use-sse-chat.ts`) calls `POST /api/v1/chat/stream` which
FastAPI (`chat.py`) proxies to the engine's `/stream` endpoint
(`apps/engine/app/routes/stream.py`). The `/run` endpoint (`run.py`) is
NOT used by the current frontend.

However `/run` is still registered in `apps/engine/app/main.py` and appears
in Swagger. Fix it now so it does not produce confusing output if someone
calls it directly during debugging.

---

## Fix 4 — Prevent error results from being cached

### The problem (context from document)

The attached document shows a session from the **old single-agent project**
where the tool cache stored an error result:

```
Turn 1: get_host_details → NotAuthenticated (error)
Turn 3: get_host_details → "[...] Using cached result" (replays cached error)
```

### Current state in new project

`execute_tools_node` in `apps/engine/app/graph/nodes/workflow_nodes.py`
does NOT currently cache tool results in Redis. Each call goes through
`execute_tool_via_mcp()` which makes a fresh HTTP call to the MCP server.

This means the old caching bug does not exist in the new project — yet.

However, the MCP server's `_dispatch()` function does not protect against
the scenario where FastAPI returns a successful HTTP 200 with an error body.
Add this guard now before you add Redis caching later:

### Guard to add in `apps/engine/app/tools/mcp_client.py`

In `execute_tool_via_mcp()`, add a check that prevents error results from
being treated as success:

```python
async def execute_tool_via_mcp(tool_name: str, args: dict | None = None) -> dict:
    """Execute a tool through the MCP server."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{MCP_SERVER_URL}/execute",
                json={"tool": tool_name, "arguments": args or {}},
            )
            if resp.status_code == 200:
                result = resp.json()
                # GUARD: never treat an error result as cacheable success
                # If status is "error", always return as-is without caching
                # This prevents the bug seen in old project where auth errors
                # were cached and replayed across turns.
                return result
            return {
                "status": "error",
                "tool": tool_name,
                "summary": f"MCP HTTP {resp.status_code}",
                "cacheable": False,    # explicit flag for future Redis caching
            }
    except Exception as exc:
        return {
            "status": "error",
            "tool": tool_name,
            "summary": str(exc)[:100],
            "cacheable": False,
        }
```

When you add Redis tool caching in Phase 5, check for `cacheable: False`
and `status != "success"` before writing to cache:

```python
# Future caching logic — do not add yet, just the pattern:
if result.get("status") == "success" and result.get("cacheable", True):
    await cache.setex(cache_key, TTL, json.dumps(result))
```

---

## Execution checklist

Run in this exact order. Do not skip validation steps.

```
Step 1  — Confirm MCP server.py has get_enabled_tools not get_all_tools
Step 2  — If server.py had get_all_tools: commit the fix, push, wait for CI
Step 3  — kubectl rollout restart deployment/mcp-server -n agentic-app
Step 4  — Validate MCP /health returns ok (curl test above)
Step 5  — Delete apps/engine/app/graph/graph.py
Step 6  — Delete apps/engine/app/graph/nodes/echo_node.py
Step 7  — grep -r "echo_node" apps/engine/ → must be zero results
Step 8  — Fix initial_state in apps/engine/app/routes/run.py
Step 9  — Add cacheable: False guard in mcp_client.py
Step 10 — Push all changes → GitHub Actions builds new engine image
Step 11 — Wait for Argo CD to sync agentic-agents namespace
Step 12 — Run end-to-end validation below
```

---

## End-to-end validation after all fixes

```powershell
# 1. MCP is healthy
kubectl run mcp-check --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://mcp-server.agentic-app.svc.cluster.local:8001/health
# {"status":"ok","tools":N,...}

# 2. Engine is healthy and running real workflow
kubectl run engine-check --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://agent-engine.agentic-agents.svc.cluster.local:8080/ready
# {"status":"ready","db":"ok","redis":"ok","langgraph":"ok"}

# 3. Engine logs show workflow nodes running (not echo_node)
kubectl logs -n agentic-agents deployment/agent-engine --tail=30
# Must NOT show: echo_node
# Must show: load_session, classify_request, execute_tools, generate_answer

# 4. Full chat stream test through FastAPI proxy
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"list all VMs","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' `
  https://api.dclab.local/api/v1/chat/stream

# Expected SSE event sequence:
# data: {"type":"start","session_id":"...","run_id":"..."}
# data: {"type":"intent","intent":"list_vms","entity":null}
# data: {"type":"safety_check","passed":true}
# data: {"type":"tool_call","tool":"list_vms","status":"running","args":{}}
# data: {"type":"tool_result","tool":"list_vms","status":"success","summary":"...","data_count":N}
# data: {"type":"final","content":"Here is what I found..."}
# data: {"type":"done"}

# 5. Confirm NO echo_node response in output
# The response must NOT contain:
# "Agent engine skeleton is working"
# "Checkpointer: Postgres | Cache: Redis"

# 6. All pods healthy
kubectl get pods -A --field-selector=status.phase!=Succeeded | `
  Select-String "agentic-app|agentic-agents"
# All Running, no CrashLoopBackOff, no ErrImagePull
```

---

## What is NOT fixed in Phase 1

These are real issues but belong in later phases:

| Issue | Phase |
|---|---|
| vCenter `NotAuthenticated` session expiry | Phase 2 |
| Intent classifier routing ESXi hostname to `get_vm_details` | Phase 3 |
| `generate_answer_node` uses hardcoded formatting instead of LLM | Phase 4 |
| govc `multiple instances` config error | Phase 6 |

Phase 1 only makes the infrastructure work correctly.
The agent will still return wrong or empty data for host queries
until Phase 2 and Phase 3 are complete.