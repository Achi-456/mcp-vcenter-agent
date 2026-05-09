# API Contract V1

This file defines the first stable FastAPI contract for the frontend and Agent
Engine. Do not change endpoint shapes without updating this document.

## Response Envelope

Success:

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

Error:

```json
{
  "ok": false,
  "error_code": "HOST_NOT_FOUND",
  "message": "No ESXi host named esxi01.dclab.com was found.",
  "details": {}
}
```

Do not return fake success with `N/A`, unknown, or zero values when the tool
actually failed.

## Required Endpoints

### Health

```text
GET /api/v1/health/services
```

Returns service health for:

```text
fastapi
agent_engine
mcp
postgres
redis
vcenter
```

FastAPI readiness must not require vCenter to be reachable.

### Tools

```text
GET /api/v1/tools
GET /api/v1/tools/{tool_name}
GET /api/v1/tools/categories
```

Tools return metadata only. Execution is separate and policy-checked.

### Connections

```text
GET  /api/v1/connections/vcenter/status
POST /api/v1/connections/vcenter/test
POST /api/v1/connections/vcenter
DELETE /api/v1/connections/vcenter
```

Never return secret values.

### Inventory

```text
GET /api/v1/inventory/overview?refresh=true
GET /api/v1/inventory/vms?refresh=true
GET /api/v1/inventory/hosts?refresh=true
GET /api/v1/inventory/datastores?refresh=true
GET /api/v1/inventory/clusters?refresh=true
GET /api/v1/inventory/networks?refresh=true
```

Support cache bypass with `refresh=true`.

### Context

```text
GET /api/v1/context/vm-details?name=<vm>
GET /api/v1/context/host-details?name=<host>
GET /api/v1/context/datastore-details?name=<datastore>
GET /api/v1/context/environment
GET /api/v1/context/search?query=<name>
```

Context endpoints return clean, LLM-ready JSON.

### Chat

```text
POST /api/v1/chat/stream
```

Request:

```json
{
  "session_id": "optional-session-id",
  "message": "get details for esxi01.dclab.com",
  "provider": "optional-provider",
  "model": "optional-model"
}
```

Response is SSE using the event contract in
`docs/knowledge/sse-event-contract.md`.

## Error Codes

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
TOOL_NOT_IMPLEMENTED
TOOL_REQUIRES_APPROVAL
TOOL_POLICY_BLOCKED
TOOL_TIMEOUT
MCP_SERVER_UNAVAILABLE
MCP_TOOL_FAILED
INTERNAL_ERROR
```

