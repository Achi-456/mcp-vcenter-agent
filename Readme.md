# vCenter Agentic Ops Platform

This repository contains the current vCenter Agentic Ops workflow: a Next.js console, a FastAPI backend, an MCP server, and a LangGraph-based agent engine for safe, read-only vCenter diagnostics.

The current agent implementation is intentionally conservative. It routes natural-language requests to known read-only diagnostics, blocks mutation or destructive requests, calls backend APIs through typed endpoints, validates the result, and streams structured SSE events back to the UI.

## Current Runtime Shape

| Service | Path | Role |
| --- | --- | --- |
| Frontend | `apps/frontend` | Next.js console for chat, inventory, diagnostics, tools, health, settings, and sessions |
| Backend API | `apps/backend` | FastAPI gateway for vCenter inventory, context helpers, tool registry, govc, vSphere REST, MCP metadata, and chat proxying |
| Agent Engine | `apps/engine` | LangGraph workflow that classifies intent, checks safety, calls backend tools, validates output, and formats final answers |
| MCP Server | `apps/mcp` | Internal MCP capability surface, exposed through safe backend-controlled routes |

Production traffic enters through the frontend and backend services in the `agentic-app` namespace. The agent engine runs separately in `agentic-agents`; backend chat routes proxy requests to the engine and stream the engine events back to the browser.

## Agentic Workflow

The active graph is defined in `apps/engine/app/graph/workflow.py`.

```text
START
  -> intent_router
  -> safety_agent
  -> route_by_intent
       -> blocked_agent
       -> general_agent
       -> tools_agent
       -> vcenter_readonly_agent
  -> validation_agent
  -> report_agent
  -> END
```

Each node reads and writes `AgentState` from `apps/engine/app/graph/state.py`. The state carries the session ID, user message, classified intent, selected tool, risk level, tool input, backend responses, findings, validation result, and final answer.

## Multi-Agent Roles

| Agent node | Purpose | Executes tools |
| --- | --- | --- |
| `intent_router` | Classifies the user message into domain, task type, object type, entity, risk level, tool name, endpoint, and input | No |
| `safety_agent` | Blocks low-risk, approval-required, and destructive actions in the current phase | No |
| `blocked_agent` | Produces a blocked finding when safety policy rejects a request | No |
| `general_agent` | Handles greetings, unsupported prompts, missing inputs, and planned Version 2 requests | No |
| `tools_agent` | Handles tool metadata requests through `/api/v1/tools` | Yes, read-only |
| `vcenter_readonly_agent` | Handles read-only vCenter, govc, vSphere REST, compare, health, and safe MCP status requests | Yes, read-only |
| `validation_agent` | Checks obvious routing or backend response errors before final output | No |
| `report_agent` | Formats the final user-facing answer from state and tool evidence | No |

This is a graph-based workflow, not an open-ended agent loop. There is no `while True` planner loop in the current implementation.

## Intent Routing

Intent classification lives in `apps/engine/app/graph/intent_router.py`.

The router currently supports:

- VM details through pyVmomi-backed context endpoints.
- Host details through pyVmomi-backed context endpoints.
- Inventory summaries for VMs, hosts, datastores, alarms, events, RKE2 VMs, and environment overview.
- Tool registry listing through `/api/v1/tools`.
- Read-only govc diagnostics such as `govc_about`, `govc_vm_info`, `govc_host_info`, datastore info, events, and volume listing.
- Read-only vSphere REST diagnostics such as appliance health, tags, content libraries, library items, attached tags, and recent tasks.
- Health summary prompts that fan out to multiple read-only backend calls.
- Compare prompts that run pyVmomi and govc diagnostics and compare scalar fields.
- Safe MCP status prompts for server info, server time, and bounded echo.

Requests for unsupported Version 2 areas, such as CSI, Kubernetes PVCs, PBM, CNS, and govmomi flows, are classified as `planned_v2` and do not select a tool.

## Safety Model

Safety is enforced before any backend tool call.

The current safety node is `apps/engine/app/graph/safety.py`. It blocks:

- `low_risk`
- `approval_required`
- `destructive`

The intent router marks mutation and shell-like requests as blocked before tool selection. Examples include power operations, maintenance mode, snapshot mutation, migration, delete, attach, detach, patch, raw govc commands, MCP command execution, and kubectl operations.

Blocked requests return a final answer that explains the safety policy and confirms that no action was taken.

## Tool Execution Path

The engine does not talk directly to vCenter. It calls backend endpoints using `BackendClient` in `apps/engine/app/clients/backend_client.py`.

```text
User prompt
  -> frontend chat UI
  -> FastAPI chat route
  -> agent engine `/run`
  -> LangGraph node selection
  -> BackendClient
  -> FastAPI backend read-only endpoint
  -> vCenter, govc, vSphere REST, MCP, or tool registry service
  -> normalized response envelope
  -> validation and final answer
```

MCP tool calls are special-cased. Only safe `mcp.default.*` status tools are routed through the backend internal MCP endpoint. The backend requires an internal token before executing those calls.

## SSE Stream

The agent engine streams structured events from `apps/engine/app/main.py`.

Typical event order:

```text
start
intent
safety_check
agent_start
tool_call
tool_result
error            # only when a backend tool returns a clean error envelope
validation
final
done
```

The backend route in `apps/backend/app/api/routes/chat.py` exposes the stream to the frontend as `text/event-stream`.

## Backend Tool Registry

Tool metadata is served from `apps/backend/app/api/routes/tools.py`.

Key endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/tools` | Lists registry tools plus discovered safe MCP tools |
| `GET /api/v1/tools/categories` | Lists tool categories |
| `GET /api/v1/tools/agents` | Lists agent ownership metadata |
| `GET /api/v1/tools/{tool_name}` | Returns one tool definition |

The frontend uses this metadata for the Tools page and settings summaries. The engine uses `/api/v1/tools` for tool-listing prompts.

## Response Validation and Reporting

Validation and answer formatting live in `apps/engine/app/graph/reporting.py`.

The validation step checks for obvious routing mistakes and backend errors, such as a host prompt being routed to a VM tool. The report step then formats a concise final answer using returned evidence. Large list results are summarized into small Markdown tables rather than dumping raw payloads.

Every final answer for the current read-only workflow ends with a clear no-mutation statement such as `No action was taken.`

## Current Boundaries

The current workflow is read-only by design.

- No destructive vCenter action executes automatically.
- No raw `govc_command` or free-form shell execution is exposed.
- Arbitrary MCP tool execution is rejected.
- Kubernetes mutation prompts are blocked.
- Secrets are never returned in chat or raw UI payloads.
- Planned Version 2 infrastructure features are acknowledged but not executed.

## Tests

The main intent and safety coverage is in `apps/engine/tests/test_intent_and_safety.py`.

That suite verifies:

- VM and host entity extraction.
- pyVmomi, govc, vSphere REST, and MCP routing.
- Missing input behavior.
- Compare diagnostics routing.
- Safety blocking for mutation and destructive prompts.
- Rejection of arbitrary MCP and shell-like requests.
- Planned Version 2 prompts not selecting tools.

For engine validation, run:

```powershell
cd apps/engine
pytest
```

For frontend build validation, run:

```powershell
cd apps/frontend
npm run build
```

## Operational Notes

The Kubernetes deployment is GitOps-driven. Application changes should be committed and pushed, GitHub Actions builds and tags images, and Argo CD syncs the cluster. Production changes should not be applied manually with ad hoc `kubectl apply`.

The live console hostname is:

```text
https://infra-agent-console.dclab.local
```
