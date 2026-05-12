# AgenticOps UI API Contracts

## Base URL

Use `NEXT_PUBLIC_API_BASE_URL`.

Default local: `http://localhost:8000`

Cluster: `https://api.dclab.local`

## Standard Success Envelope

```json
{
  "ok": true,
  "data": {},
  "metadata": {}
}
```

## Standard Error Envelope

```json
{
  "ok": false,
  "error_code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}
```

## Main APIs

Health:
- `GET /api/v1/health/services`
- `GET /api/v1/connections/vcenter/status`

Tools:
- `GET /api/v1/tools`
- `GET /api/v1/tools/categories`
- `GET /api/v1/tools/agents`

Inventory:
- `GET /api/v1/inventory/vms`
- `GET /api/v1/inventory/hosts`
- `GET /api/v1/inventory/datastores`

Context:
- `GET /api/v1/context/environment`
- `GET /api/v1/context/datastore-health`
- `GET /api/v1/context/vm-details?name=`
- `GET /api/v1/context/host-details?name=`

Monitoring:
- `GET /api/v1/monitoring/alarms`
- `GET /api/v1/monitoring/events?limit=50`

govc:
- `GET /api/v1/govc/about`
- `GET /api/v1/govc/vm-info?name=`
- `GET /api/v1/govc/host-info?name=`
- `GET /api/v1/govc/datastore-info`
- `GET /api/v1/govc/events`
- `GET /api/v1/govc/volume-ls`

vSphere REST:
- `GET /api/v1/vsphere-rest/about`
- `GET /api/v1/vsphere-rest/appliance/health`
- `GET /api/v1/vsphere-rest/tags`
- `GET /api/v1/vsphere-rest/tag-categories`
- `GET /api/v1/vsphere-rest/content-libraries`
- `GET /api/v1/vsphere-rest/tasks/recent`

MCP:
- `GET /api/v1/mcp/servers/default/status`
- `GET /api/v1/mcp/tools`

Chat:
- `POST /api/v1/chat/stream`
- `POST /api/v1/agent/run`

Never call the MCP server directly from the frontend.
Never call internal MCP execution endpoints from the frontend.
