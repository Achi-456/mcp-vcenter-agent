# AgenticOps UI Page Map

Initial frontend pages:

- `/` Dashboard
- `/chat` AI Assistant
- `/inventory` Inventory overview
- `/diagnostics` Diagnostics
- `/tools` Tool registry
- `/health` System health
- `/settings` Settings scaffold
- `/sessions` Sessions scaffold

## Dashboard

Purpose: quick vCenter operations overview.

Top metric cards:
- Total VMs
- Powered On
- ESXi Hosts
- Datastores
- Active Alarms
- Critical Datastores
- Recent Events
- Agent Health

Dashboard sections:
- Environment Overview
- Datastore Health
- Active Alarms
- Recent Events
- AI Suggested Checks

API mapping:
- `GET /api/v1/context/environment`
- `GET /api/v1/inventory/vms`
- `GET /api/v1/inventory/hosts`
- `GET /api/v1/inventory/datastores`
- `GET /api/v1/context/datastore-health`
- `GET /api/v1/monitoring/alarms`
- `GET /api/v1/monitoring/events?limit=50`
- `GET /api/v1/health/services`

UX rules:
- manual refresh button
- auto refresh every 2 minutes
- keep previous data visible while refreshing
- show last updated time
- show degraded state if one endpoint fails
- do not show blank cards

## AI Assistant

Layout:
- chat conversation column
- session/tool rail column
- fixed expandable input

Chat event mapping:
- `start` -> Session started
- `intent` -> IntentCard
- `safety_check` -> SafetyCard
- `agent_start` -> AgentCard
- `tool_call` -> ToolCallCard
- `tool_result` -> ToolResultCard
- `validation` -> ValidationCard
- `final` -> Markdown answer
- `error` -> ErrorCard
- `done` -> stop loading

Prompt suggestions:
- `check roshellevm02`
- `summarize vCenter health`
- `critical datastores?`
- `show active alarms`
- `compare pyVmomi and govc for roshellevm02`
- `verify roshellevm02 with govc`
- `show vSphere tags`
- `test MCP`

Important UX rules:
- tool trace collapsed by default
- final answer always visible
- View raw JSON expandable
- Copy answer button
- Copy raw result button
- blocked action UI uses red/amber and states "No action was taken."

## Inventory

Tabs:
- Virtual Machines
- Hosts
- Datastores

Future tabs:
- Networks
- Clusters
- Resource Pools

VM table columns:
- Name
- Power State
- CPU
- Memory
- Guest OS
- IP Address
- Host
- Datastore
- Tools Status

Host table columns:
- Name
- Connection State
- Power State
- Version
- Build
- Vendor
- Model
- CPU Cores
- Memory
- VM Count

Datastore table columns:
- Name
- Type
- Capacity
- Free
- Used %
- Health
- Accessible

Features:
- search
- sort
- filter by power state
- filter by tools status
- refresh
- auto-refresh every 2 minutes
- row details drawer

## Diagnostics

Tabs:
- pyVmomi
- govc
- vSphere REST
- Compare
- MCP

pyVmomi actions:
- Inspect VM
- Inspect Host
- Datastore Health
- Active Alarms
- Recent Events
- Environment Overview

govc actions:
- govc about
- VM info
- Host info
- Datastore info
- Events
- Volume list

vSphere REST actions:
- Appliance health
- Tags
- Tag categories
- Attached tags
- Content libraries
- Recent tasks

If recent tasks returns `ok=false`, show provider-limited state, not fake success.

Compare forms:
- VM name -> compare pyVmomi vs govc
- Host name/IP -> compare pyVmomi vs govc
- Datastore compare

MCP actions:
- MCP server info
- MCP server time
- Safe echo test

MCP tab rules:
- show safe tools only
- no arbitrary MCP execution
- no raw tool selector

## Tools

Use Tool Registry as a governance page.

Columns:
- Tool Name
- Display Name
- Backend
- Category
- Agent
- Risk Level
- Enabled
- Implemented
- Requires Approval

Group by backend:
- pyVmomi
- govc
- vSphere REST
- MCP
- Disabled / Future

Badge rules:
- `read_only` -> green
- `approval_required` -> amber
- `destructive` -> red
- enabled -> blue/green
- disabled -> gray
- implemented -> blue
- not implemented -> gray

## System Health

Services:
- FastAPI
- Agent Engine
- Postgres
- Redis
- vCenter
- MCP Gateway
- MCP Server

APIs:
- `GET /api/v1/health/services`
- `GET /api/v1/connections/vcenter/status`
- `GET /api/v1/mcp/servers/default/status`

UX rules:
- no infinite Checking state
- checking must timeout into Degraded, Offline, or Unknown
- each service card shows name, status, latency if available, last checked, and details

## Settings

Version 1 settings are simple and safe.

Sections:
- vCenter Connection
- LLM Provider Status
- MCP Internal Status
- UI Preferences

vCenter section:
- configured/not configured
- vCenter URL
- username hint
- secret reference
- test connection
- reconnect
- never show password

LLM provider section:
- provider configured status
- default provider
- default model
- connect button if missing key
- never show API key

MCP section:
- MCP Gateway status
- MCP Server status
- safe tools count
- internal execution enabled status
- never show internal token

## Sessions

Version 1 minimal fields:
- Session ID
- Created time
- Last updated
- Last prompt
- Tool count
- Status
- Open

Future:
- audit timeline
- export report
- investigation notes

Phase 9A only wires:
- Dashboard to health summary
- Tools page to tool registry
- System Health page to service health

Later phases:
- Phase 9B: full chat SSE renderer
- Phase 9C: dashboard health cards and service summaries
- Phase 9D: inventory tables
- Phase 9E: diagnostics and tools
- Phase 9F: settings and sessions
