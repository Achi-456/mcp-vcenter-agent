# AgenticOps FastAPI Backend Architecture Knowledge

## Purpose

This document is for the `knowledge/` folder. It explains how the FastAPI backend should be structured to support:

- LangGraph Agent Engine
- LangChain chains/tools/parsers
- MCP servers and MCP tool gateways
- pyVmomi vCenter tools
- govc read-only fallback tools
- govmomi CNS/CSI tools
- vSphere REST API tools
- Kubernetes/RKE2/CSI tools
- Observability, GitOps, and security tools
- Session persistence, caching, audit, and approvals

The backend must be designed as a **safe infrastructure API gateway**, not just a simple web API.

---

## References Used

This design follows these public design principles:

1. FastAPI recommends structuring bigger applications with multiple files and `APIRouter`, similar to Flask Blueprints:
   - https://fastapi.tiangolo.com/tutorial/bigger-applications/

2. FastAPI `APIRouter` is designed to group path operations and include them in the main app:
   - https://fastapi.tiangolo.com/reference/apirouter/

3. FastAPI lifespan events are recommended for startup/shutdown logic such as initializing clients, connection pools, and shared resources:
   - https://fastapi.tiangolo.com/advanced/events/

4. FastAPI dependency injection is intended to make shared components easier to integrate into endpoints:
   - https://fastapi.tiangolo.com/tutorial/dependencies/

5. MCP tools are server-exposed functions that models can invoke; each tool has a unique name and metadata/schema:
   - https://modelcontextprotocol.io/specification/2025-06-18/server/tools

6. MCP supports resources, prompts, and tools as major server capabilities:
   - https://modelcontextprotocol.io/specification/2025-11-25

7. MCP authorization should protect sensitive tool operations and resources:
   - https://modelcontextprotocol.io/docs/tutorials/security/authorization

8. MCP servers can introduce security risks if unsafe tool execution or STDIO command handling is exposed. For this platform, do not expose free-form shell tools or unrestricted command execution:
   - https://www.tomshardware.com/tech-industry/artificial-intelligence/anthropics-model-context-protocol-has-critical-security-flaw-exposed

---

# 1. Backend Design Goal

The FastAPI backend is the **control gateway** between:

```text
Frontend / Next.js
Agent Engine / LangGraph
MCP servers
vCenter
Kubernetes/RKE2
Observability systems
GitOps systems
Storage/CNS
Security scanners
Postgres/Redis
```

The backend should provide:

```text
1. Stable REST APIs for frontend pages
2. Secure credential handling
3. Read-only infrastructure tools
4. Safe execution gateway for Agent Engine tools
5. SSE proxy for chat streaming
6. Tool registry and metadata
7. Health/status endpoints
8. Audit logging
9. Cache and session support
10. Approval workflow foundation
```

---

# 2. High-Level Architecture

```text
Next.js Frontend
  ↓
FastAPI Backend
  ├── REST APIs for dashboard/inventory/settings/health
  ├── SSE chat gateway
  ├── Tool registry API
  ├── Credential/secret manager
  ├── Infrastructure tool services
  ├── MCP client/gateway
  ├── Audit + session APIs
  └── Health/status APIs
        ↓
      Agent Engine
        ↓
      LangGraph workflows
        ↓
      MCP / FastAPI tools
        ↓
      vCenter / Kubernetes / Observability / GitOps
```

FastAPI should be the only browser-facing backend. The browser should **not** call the Agent Engine or MCP servers directly.

---

# 3. Backend Responsibilities

## 3.1 Frontend API Gateway

Expose stable APIs for:

```text
/api/v1/dashboard/*
/api/v1/inventory/*
/api/v1/monitoring/*
/api/v1/settings/*
/api/v1/connections/*
/api/v1/health/*
/api/v1/chat/*
/api/v1/tools/*
```

The UI depends on these APIs.

---

## 3.2 Agent Gateway

FastAPI proxies chat requests to the Agent Engine.

```text
Browser
  ↓
POST /api/v1/chat/stream
  ↓
FastAPI agent_client.py
  ↓
Agent Engine /stream
  ↓
SSE back to browser
```

The frontend should not know internal Agent Engine service URLs.

---

## 3.3 Tool Gateway

FastAPI exposes infrastructure tool endpoints that the Agent Engine and MCP servers can call.

Examples:

```text
/api/v1/context/vm-details
/api/v1/context/host-details
/api/v1/csi/va-check
/api/v1/govc/vm-info
/api/v1/vsphere-rest/tags
```

---

## 3.4 Credential and Secret Manager

FastAPI manages credentials through Kubernetes Secrets.

Secrets should never be returned to the frontend.

Examples:

```text
agentic-vcenter-default
agentic-llm-gemini
agentic-llm-openai
agentic-llm-anthropic
agentic-llm-xai
agentic-llm-moonshot
agentic-postgres-secret
agentic-redis-secret
```

---

## 3.5 Safety and Policy Enforcement

FastAPI should enforce policy at API boundaries.

Even if the Agent Engine makes a mistake, FastAPI should block:

```text
- VM power operations
- host maintenance mode
- datastore delete/unmount
- snapshot delete/revert
- CNS volume delete
- Kubernetes patch/delete
- arbitrary govc command
```

Current phase:

```text
Only read_only operations are allowed automatically.
```

---

# 4. Recommended FastAPI Folder Structure

```text
apps/backend/app/
├── main.py
├── api/
│   ├── deps.py
│   └── routes/
│       ├── dashboard.py
│       ├── inventory.py
│       ├── monitoring.py
│       ├── context.py
│       ├── connections.py
│       ├── settings.py
│       ├── chat.py
│       ├── tools.py
│       ├── health.py
│       ├── k8s.py
│       ├── csi.py
│       ├── govc.py
│       ├── vsphere_rest.py
│       ├── approvals.py
│       ├── audit.py
│       └── sessions.py
│
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── security.py
│   ├── errors.py
│   ├── middleware.py
│   └── lifespan.py
│
├── schemas/
│   ├── common.py
│   ├── inventory.py
│   ├── monitoring.py
│   ├── context.py
│   ├── connections.py
│   ├── chat.py
│   ├── tools.py
│   ├── health.py
│   ├── k8s.py
│   ├── csi.py
│   ├── govc.py
│   ├── vsphere_rest.py
│   ├── approvals.py
│   └── audit.py
│
├── services/
│   ├── vcenter_session.py
│   ├── vcenter_inventory_service.py
│   ├── vcenter_monitoring_service.py
│   ├── vcenter_context_service.py
│   ├── k8s_client.py
│   ├── csi_service.py
│   ├── govc_service.py
│   ├── vsphere_rest_service.py
│   ├── mcp_client.py
│   ├── mcp_gateway.py
│   ├── agent_client.py
│   ├── secret_store.py
│   ├── tool_registry_service.py
│   ├── policy_service.py
│   ├── approval_service.py
│   ├── audit_service.py
│   ├── cache_service.py
│   ├── health_service.py
│   └── report_service.py
│
├── repositories/
│   ├── session_repository.py
│   ├── audit_repository.py
│   ├── approval_repository.py
│   ├── report_repository.py
│   └── tool_run_repository.py
│
├── db/
│   ├── session.py
│   ├── models.py
│   ├── migrations/
│   └── init.py
│
├── clients/
│   ├── redis_client.py
│   ├── postgres_client.py
│   ├── http_client.py
│   └── k8s_api_client.py
│
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

---

# 5. Router Design

Use one router per domain. FastAPI `APIRouter` is designed for this type of modular routing.

## Main app

```python
from fastapi import FastAPI
from app.api.routes import (
    dashboard,
    inventory,
    monitoring,
    context,
    connections,
    chat,
    tools,
    health,
    k8s,
    csi,
    govc,
    vsphere_rest,
)

app = FastAPI(title="AgenticOps API")

app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(k8s.router, prefix="/api/v1/k8s", tags=["kubernetes"])
app.include_router(csi.router, prefix="/api/v1/csi", tags=["csi"])
app.include_router(govc.router, prefix="/api/v1/govc", tags=["govc"])
app.include_router(vsphere_rest.router, prefix="/api/v1/vsphere-rest", tags=["vsphere-rest"])
```

---

# 6. Lifespan Startup / Shutdown

Use FastAPI lifespan to initialize and close shared resources.

Initialize:

```text
- Redis client
- Postgres pool
- HTTP client
- Kubernetes client
- vCenter session manager
- Tool registry
- MCP clients
```

Shutdown:

```text
- close HTTP client
- close Redis
- close DB pool
- disconnect vCenter session
- close MCP connections
```

Example:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_client()
    app.state.db = await create_db_pool()
    app.state.http = create_http_client()
    app.state.tool_registry = load_tool_registry()
    app.state.vcenter_session = VCenterSession(...)
    app.state.mcp_gateway = MCPGateway(...)

    yield

    await app.state.http.aclose()
    await app.state.redis.close()
    await app.state.db.close()
    app.state.vcenter_session.disconnect()
```

---

# 7. Dependency Injection Pattern

Use FastAPI dependencies for shared services.

```python
def get_vcenter_session(request: Request) -> VCenterSession:
    return request.app.state.vcenter_session

def get_tool_registry(request: Request) -> ToolRegistryService:
    return request.app.state.tool_registry

def get_policy_service(request: Request) -> PolicyService:
    return request.app.state.policy_service
```

This avoids creating new clients on every request.

---

# 8. Core Service Layers

## 8.1 VCenterSession Service

The backend must not create a fresh `SmartConnect` for every tool call.

Use a persistent session manager:

```text
VCenterSession:
- load credentials from Kubernetes Secret
- create SmartConnect once
- check currentSession before each call
- reconnect if session expired
- retry once on NotAuthenticated
- never log password
```

Service file:

```text
services/vcenter_session.py
```

All pyVmomi services should use:

```python
vcenter_session.run(lambda si, content: ...)
```

---

## 8.2 Kubernetes Client Service

Service file:

```text
services/k8s_client.py
```

Responsibilities:

```text
- use in-cluster config first
- fallback to kubeconfig for local dev
- list pods, nodes, PVCs, PVs, StorageClasses, VolumeAttachments, events
- return safe normalized JSON
```

RBAC must be read-only.

---

## 8.3 govc Service

Service file:

```text
services/govc_service.py
```

Rules:

```text
- read vCenter credentials from secret store
- set GOVC_URL, GOVC_USERNAME, GOVC_PASSWORD, GOVC_INSECURE
- run only whitelisted commands
- timeout every command
- never log GOVC_PASSWORD
- parse JSON when possible
- block destructive commands
```

Allowed:

```text
about
find
vm.info
host.info
datastore.info
events
volume.ls
```

Blocked:

```text
vm.power
vm.destroy
snapshot.remove
host.maintenance.enter
datastore.rm
object.destroy
volume.rm
```

---

## 8.4 vSphere REST Service

Service file:

```text
services/vsphere_rest_service.py
```

Responsibilities:

```text
- create REST session
- reuse or refresh session
- get appliance health
- tags/categories
- content libraries
- recent tasks
- lightweight inventory summaries
```

Do not expose REST session tokens to frontend or LLM.

---

## 8.5 MCP Gateway Service

Service file:

```text
services/mcp_gateway.py
```

Responsibilities:

```text
- register MCP servers
- discover MCP tools
- normalize tool metadata into internal ToolSpec
- call MCP tools safely
- enforce risk policy before tool call
- timeout every MCP call
- convert MCP errors into standard FastAPI error responses
```

MCP tools are powerful because they can access external systems. Treat them as untrusted unless registered and approved.

---

## 8.6 Agent Client Service

Service file:

```text
services/agent_client.py
```

Responsibilities:

```text
- call Agent Engine internal service
- proxy SSE stream to frontend
- apply request validation
- attach session_id, user info, provider/model
- handle agent timeout and errors
```

Frontend should only call FastAPI:

```text
POST /api/v1/chat/stream
```

---

## 8.7 Tool Registry Service

Service file:

```text
services/tool_registry_service.py
```

Every tool should have:

```json
{
  "name": "get_host_details",
  "display_name": "Get Host Details",
  "description": "Get read-only ESXi host details.",
  "domain": "vcenter",
  "category": "Inventory",
  "agent": "vcenter_pyvmomi_agent",
  "backend": "pyvmomi",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false,
  "input_schema": {
    "host_name": "string"
  },
  "output_schema": {
    "name": "string",
    "connection_state": "string"
  }
}
```

Tool registry sources:

```text
- static YAML/JSON files
- MCP tool discovery
- backend route metadata
```

---

## 8.8 Policy Service

Service file:

```text
services/policy_service.py
```

Responsibilities:

```text
- check tool risk level
- allow read_only
- block destructive
- require approval for approval_required
- enforce namespace/resource restrictions
- block free-form command execution
```

Policy check must happen in:

```text
1. Agent Engine
2. FastAPI Tool Gateway
3. MCP Gateway
```

Defense in depth.

---

## 8.9 Audit Service

Service file:

```text
services/audit_service.py
```

Audit every tool call:

```text
- run_id
- session_id
- user_id
- tool_name
- risk_level
- input summary
- output summary
- status
- started_at
- completed_at
- error_code
```

Do not store secrets.

---

# 9. API Groups

## 9.1 Health APIs

```text
GET /api/v1/health
GET /api/v1/health/services
GET /api/v1/agent/health
```

Return:

```json
{
  "fastapi": {"status": "online"},
  "agent_engine": {"status": "online"},
  "redis": {"status": "online"},
  "postgres": {"status": "online"},
  "vcenter": {"status": "online"}
}
```

Do not leave frontend stuck at `Checking`.

---

## 9.2 Connections APIs

```text
POST /api/v1/connections/vcenter/test
POST /api/v1/connections/vcenter
GET  /api/v1/connections/vcenter/status
POST /api/v1/connections/vcenter/reconnect
DELETE /api/v1/connections/vcenter
```

LLM providers:

```text
GET  /api/v1/llm/providers
GET  /api/v1/llm/models?provider=gemini
GET  /api/v1/llm/status?provider=gemini
POST /api/v1/connections/llm/provider/test
POST /api/v1/connections/llm/provider
DELETE /api/v1/connections/llm/provider/{provider}
```

---

## 9.3 Inventory APIs

```text
GET /api/v1/inventory/overview
GET /api/v1/inventory/vms
GET /api/v1/inventory/hosts
GET /api/v1/inventory/clusters
GET /api/v1/inventory/datastores
GET /api/v1/inventory/networks
```

Support:

```text
?refresh=true
?page=
?limit=
?search=
?sort=
?filter=
```

Important UX rule:

```text
Frontend should keep old data during refresh.
Backend should support cache bypass with refresh=true.
```

---

## 9.4 Context APIs

For chat-friendly object lookup.

```text
GET /api/v1/context/vm-details?name=<vm>
GET /api/v1/context/host-details?name=<host>
GET /api/v1/context/datastore-details?name=<datastore>
GET /api/v1/context/environment
GET /api/v1/context/powered-off-vms
GET /api/v1/context/datastore-health
GET /api/v1/context/rke2-vms
GET /api/v1/context/search?query=<name>
```

Context APIs should return clean, safe, LLM-ready JSON.

---

## 9.5 Kubernetes APIs

```text
GET /api/v1/k8s/nodes
GET /api/v1/k8s/pods
GET /api/v1/k8s/csi/pods
GET /api/v1/k8s/csi/drivers
GET /api/v1/k8s/storageclasses
GET /api/v1/k8s/pvcs
GET /api/v1/k8s/pvs
GET /api/v1/k8s/volumeattachments
GET /api/v1/k8s/events
```

Read-only only.

---

## 9.6 CSI APIs

```text
GET /api/v1/csi/overview
GET /api/v1/csi/va-check
GET /api/v1/csi/pvc-health
GET /api/v1/csi/volume-attachments
GET /api/v1/csi/storageclass-health
GET /api/v1/csi/datastore-health
```

CSI VA Check should combine:

```text
- CSI pods
- CSIDriver
- StorageClasses
- PVCs
- PVs
- VolumeAttachments
- vCenter datastore health
- vCenter storage alarms/events
- CNS mapping when available
```

---

## 9.7 govc APIs

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

No free-form `govc_command` endpoint unless strictly whitelisted.

---

## 9.8 vSphere REST APIs

```text
GET /api/v1/vsphere-rest/about
GET /api/v1/vsphere-rest/appliance/health
GET /api/v1/vsphere-rest/tags
GET /api/v1/vsphere-rest/tags/attached?object_id=<id>
GET /api/v1/vsphere-rest/content-libraries
GET /api/v1/vsphere-rest/tasks/recent
```

---

## 9.9 Tool APIs

```text
GET /api/v1/tools
GET /api/v1/tools/{tool_name}
GET /api/v1/tools/categories
GET /api/v1/tools/agents
```

Optional internal execution endpoint:

```text
POST /api/v1/tools/execute
```

If implemented, it must:

```text
- require internal auth
- validate input schema
- check policy
- audit the call
- block non-read-only unless approved
```

---

## 9.10 Chat APIs

```text
POST /api/v1/chat/stream
GET  /api/v1/chat/sessions
GET  /api/v1/chat/sessions/{session_id}
DELETE /api/v1/chat/sessions/{session_id}
```

SSE events:

```text
start
intent
safety_check
plan
agent_start
tool_call
tool_result
finding
validation
final
error
done
```

---

# 10. Standard Response Format

Use consistent response envelopes.

## Success

```json
{
  "ok": true,
  "data": {},
  "metadata": {
    "source": "pyvmomi",
    "cached": false,
    "collected_at": "2026-05-10T10:00:00Z"
  }
}
```

## Error

```json
{
  "ok": false,
  "error_code": "HOST_NOT_FOUND",
  "message": "No ESXi host named esxi01.dclab.com was found.",
  "details": {
    "suggested_tool": "search_inventory_object"
  }
}
```

Do not return fake success with unknown/N/A/0 values.

---

# 11. Error Codes

Use predictable error codes.

```text
VCENTER_NOT_CONFIGURED
VCENTER_AUTH_FAILED
VCENTER_SESSION_EXPIRED
VCENTER_UNREACHABLE
VCENTER_SSL_ERROR
VCENTER_INVENTORY_ERROR

VM_NOT_FOUND
HOST_NOT_FOUND
DATASTORE_NOT_FOUND
WRONG_OBJECT_TYPE

K8S_API_UNAVAILABLE
K8S_RBAC_DENIED
CSI_COMPONENT_NOT_FOUND
PVC_NOT_FOUND
PV_NOT_FOUND

PROVIDER_NOT_CONNECTED
MODEL_FETCH_FAILED
LLM_AUTH_FAILED

TOOL_NOT_FOUND
TOOL_DISABLED
TOOL_REQUIRES_APPROVAL
TOOL_POLICY_BLOCKED
TOOL_TIMEOUT
MCP_SERVER_UNAVAILABLE
MCP_TOOL_FAILED

INTERNAL_ERROR
```

---

# 12. Cache Strategy

Use Redis for:

```text
- inventory overview
- VM/host/datastore list
- CSI VA intermediate results
- tool results
- provider model lists
```

Do not cache:

```text
- auth failures
- NotAuthenticated
- VCENTER_SESSION_EXPIRED
- permission errors
- destructive operations
- approval decisions without TTL
```

Cache TTL suggestions:

```text
inventory overview: 30s
VM list: 60s
host list: 60s
datastore health: 60s
events: 30s
CSI VA check: 60s to 120s
provider models: 10m
```

Support:

```text
?refresh=true
```

to bypass cache.

---

# 13. Security Model

## 13.1 Secrets

Never return:

```text
password
api_key
access_token
refresh_token
private_key
GOVC_PASSWORD
vCenter session ID
REST session token
```

Never log secrets.

---

## 13.2 Tool Risk Enforcement

Every tool must have:

```text
risk_level
enabled
implemented
requires_approval
```

Execution rules:

```text
read_only → allowed
low_risk → confirmation later
approval_required → block until approval workflow
destructive → disabled
```

---

## 13.3 MCP Security

MCP tools should be treated as external capability providers.

Rules:

```text
- register only trusted MCP servers
- do not expose arbitrary shell/stdin tools
- require auth for MCP server calls
- apply policy before calling any MCP tool
- timeout every MCP tool call
- audit every MCP call
- validate tool input schema
```

Avoid free-form command execution.

---

## 13.4 Kubernetes RBAC

FastAPI service account should get only read-only permissions unless approval workflow is implemented.

For CSI:

```text
pods
nodes
persistentvolumes
persistentvolumeclaims
events
namespaces
storageclasses
csidrivers
volumeattachments
deployments
daemonsets
statefulsets
replicasets
```

Verbs:

```text
get, list, watch
```

---

# 14. Database Design

## Tables

```text
chat_sessions
chat_messages
agent_runs
tool_calls
audit_events
approval_requests
reports
tool_registry_snapshots
```

## chat_sessions

```text
id
title
provider
model
created_at
updated_at
status
```

## agent_runs

```text
id
session_id
user_message
task_type
risk_level
status
started_at
completed_at
error_code
```

## tool_calls

```text
id
run_id
tool_name
agent_name
risk_level
status
input_summary
output_summary
error_code
started_at
completed_at
```

## audit_events

```text
id
actor
action
resource_type
resource_name
risk_level
status
created_at
metadata_json
```

## approval_requests

```text
id
run_id
tool_name
requested_action
risk_level
status
requested_by
approved_by
created_at
decided_at
reason
```

---

# 15. Background Jobs

Long tasks should not block FastAPI workers forever.

Use one of these:

```text
- Celery
- RQ
- Arq
- FastAPI BackgroundTasks for small jobs only
- Kubernetes Jobs for heavy scanners
```

For the current phase, streaming chat can call tools directly if they are quick.

For heavy work:

```text
CSI VA check
security scan
large inventory report
```

use background job + stream progress events.

---

# 16. Observability

Expose metrics:

```text
- API request count
- API latency
- tool call count
- tool call latency
- tool failure count
- vCenter reconnect count
- cache hit/miss
- MCP server health
- Agent Engine health
```

Add structured logs:

```json
{
  "event": "tool_call",
  "run_id": "...",
  "tool": "get_host_details",
  "risk_level": "read_only",
  "status": "success",
  "duration_ms": 842
}
```

No secrets in logs.

---

# 17. Testing Strategy

## Unit tests

```text
- policy_service blocks risky tools
- govc_service blocks destructive commands
- vcenter_session retries once on NotAuthenticated
- tool registry filters by agent/risk
- error mapper returns correct codes
```

## Integration tests

```text
- /api/v1/context/host-details
- /api/v1/context/vm-details
- /api/v1/csi/va-check
- /api/v1/govc/about
- /api/v1/tools
- /api/v1/chat/stream
```

## Contract tests

Agent Engine expects:

```text
- stable tool schemas
- stable response envelope
- stable error codes
- stable SSE events
```

## Security tests

```text
- no secret appears in API response
- govc destructive commands blocked
- MCP unregistered tool blocked
- Kubernetes write verbs not allowed
- approval_required tools blocked
```

---

# 18. Deployment Considerations

## Kubernetes manifests

```text
deployment.yaml
service.yaml
ingress.yaml
serviceaccount.yaml
rbac.yaml
configmap.yaml
secret references
networkpolicy.yaml
```

## Health probes

```text
/readiness
/liveness
/api/v1/health
```

Readiness should check:

```text
- app started
- Redis optional
- Postgres optional
- tool registry loaded
```

Do not make vCenter required for API pod readiness. vCenter may be temporarily down, but API should still serve settings/status pages.

---

# 19. Recommended Implementation Roadmap

## Fix B1 — Backend Foundation

```text
- Clean app structure
- APIRouter organization
- lifespan service initialization
- common response envelope
- common error codes
```

## Fix B2 — Service Layer

```text
- VCenterSession singleton
- k8s_client
- govc_service
- vsphere_rest_service
- secret_store
```

## Fix B3 — Tool Registry + Policy

```text
- ToolSpec model
- registry endpoints
- policy enforcement
- audit tool calls
```

## Fix B4 — MCP Gateway

```text
- MCP server registration
- tool discovery
- schema normalization
- MCP call wrapper
- policy before MCP call
```

## Fix B5 — CSI APIs

```text
- Kubernetes read-only endpoints
- CSI VA check endpoint
- datastore/alarms correlation
```

## Fix B6 — Chat Gateway

```text
- SSE proxy
- session handling
- run tracking
- error streaming
```

## Fix B7 — Observability + Audit

```text
- structured logging
- metrics
- audit repository
- report artifacts
```

---

# 20. Codex Implementation Prompt

Use this prompt with Codex.

```text
You are working on the AgenticOps vCenter Agentic Ops Platform.

Create a well-structured FastAPI backend architecture for supporting:
- LangGraph Agent Engine
- LangChain nodes/chains
- MCP tool servers
- pyVmomi tools
- govc read-only tools
- govmomi CNS/CSI tools
- vSphere REST API tools
- Kubernetes/RKE2/CSI tools
- Observability/GitOps/security tools

Read this knowledge file first.

Core requirements:
1. FastAPI is the browser-facing API gateway.
2. Browser must not call Agent Engine or MCP servers directly.
3. Use APIRouter per domain.
4. Use lifespan startup/shutdown for shared clients.
5. Use dependency injection for shared services.
6. Separate routers, schemas, services, repositories, clients, policies.
7. Every tool must have ToolSpec metadata.
8. Enforce risk policy before every tool call.
9. Only read_only tools execute automatically.
10. approval_required/destructive tools must be blocked.
11. Never expose secrets.
12. Never expose raw govc command.
13. MCP tools must be registered, schema-validated, policy-checked, timed out, and audited.
14. Use common response envelope and error codes.
15. Add audit trail for every tool call.
16. Add Redis caching but do not cache auth failures.
17. Add health/status endpoints.
18. Add CSI/Kubernetes read-only endpoints.
19. Add govc read-only endpoints.
20. Add vSphere REST read-only endpoints for tags/content library/tasks.

Expected structure:
apps/backend/app/api/routes/
apps/backend/app/core/
apps/backend/app/schemas/
apps/backend/app/services/
apps/backend/app/repositories/
apps/backend/app/db/
apps/backend/app/clients/
apps/backend/app/tests/

Implement in phases:
B1 backend foundation
B2 service layer
B3 tool registry + policy
B4 MCP gateway
B5 CSI APIs
B6 chat gateway
B7 observability/audit
```

---

# 21. Final Architecture Summary

The FastAPI backend should be:

```text
- modular
- domain-based
- service-oriented
- policy-enforced
- audit-friendly
- cache-aware
- MCP-ready
- Agent Engine-ready
- safe by default
```

The most important backend rule:

```text
FastAPI is not only an API server.
FastAPI is the protected infrastructure tool gateway.
```

Every infrastructure action must pass through:

```text
schema validation
policy check
secret-safe execution
timeout
audit log
safe response formatting
```
