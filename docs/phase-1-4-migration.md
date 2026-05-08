# Phase 1.4 — MCP Server Tool Registry

## Architecture Decision

The canonical tool registry lives in the **MCP Server** (`apps/mcp/`), not the Agent Engine. Per AGENTS.md, the MCP server is the source of truth for tool definitions, schemas, and execution. The Agent Engine queries the MCP server for tool discovery and dispatch.

```
Frontend → FastAPI → Agent Engine → MCP Server → vCenter (pyVmomi)
                    ↑ proxy                 ↑ tool registry + execution
```

## Tool Categories

| Category | Tools | Phase |
|---|---|---|
| **Inventory & Information** | list_vms, get_vm_details, list_hosts, get_host_details, get_vcenter_info, list_datastores, list_networks, list_clusters, get_vm_stats | 1.4 |
| **VM Management** | power_on_vm, power_off_vm, reboot_guest, reset_vm, suspend_vm, create_vm, clone_vm, delete_vm, rename_vm, migrate_vm, change_vm_network | Future |
| **VM Snapshots** | list_snapshots, create_snapshot, revert_to_snapshot, delete_snapshot | Future |
| **Host Management** | enter_maintenance_mode, exit_maintenance_mode | Future |
| **Monitoring & Events** | get_active_alarms, get_recent_events | 1.4 |
| **Context Helpers** | get_environment_overview, get_powered_off_vms, get_datastore_health, get_rke2_vms | 1.4 |
| **General & Utility** | list_available_tools, govc_command, web_search | 1.4/Partial |

## Risk Levels

| Level | Phase 1.4 Behavior |
|---|---|
| `read_only` | Fully enabled, executable |
| `low_risk` | Listed but disabled |
| `approval_required` | Listed, marked "Approval required", blocked |
| `destructive` | Listed, marked "Destructive / disabled", blocked |

## Key Design Decisions

1. **MCP server is the tool registry** — tools defined once in `apps/mcp/app/tools/registry.py`, consumed by engine and FastAPI
2. **Engine calls MCP for tools** — `GET http://mcp-server.agentic-app.svc:8081/tools` for discovery
3. **Engine calls MCP for execution** — `POST http://mcp-server.agentic-app.svc:8081/execute` for tool dispatch
4. **Dangerous tools are visible but blocked** — listed in registry with `enabled: false`, `risk: "destructive"`
5. **VM details via pyVmomi only** — no govc free-form shell commands for VM inspection

## Migration Map — Old → New

| Old (Local Docker) | New (RKE2 Cluster) |
|---|---|
| `app/tools/vcenter.py` — all tools in one file | `apps/mcp/app/tools/` — structured registry + execution modules |
| `app/tools/registry.py` — dynamic introspection | `apps/mcp/app/tools/registry.py` — static `ToolDef` dataclass list |
| `app/agent/engine.py` — multi-turn while-loop | `apps/engine/app/graph/` — LangGraph nodes |
| `app/agent/safety.py` — CLI confirmation | `apps/engine/app/safety/classifier.py` — pattern-based blocking |
| `app/ui/pages/agent.py` — NiceGUI run log | `apps/frontend/components/chat/ai-assistant-panel.tsx` — React SSE panel |
| `app/agent/prompts.py` — system prompts | `apps/engine/app/graph/nodes/` — injected per-node |
| Global singleton `_conn` | K8s Secret-backed factory pattern |