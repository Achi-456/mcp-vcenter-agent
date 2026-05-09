# Tool Risk Policy

Every tool must have explicit risk metadata before it can be listed or executed.

## Risk Levels

| Risk level | Meaning | Current behavior |
| --- | --- | --- |
| `read_only` | Queries state only and makes no infrastructure changes | Allowed automatically |
| `low_risk` | Small reversible change or low operational risk | Blocked for now |
| `approval_required` | State-changing operation that needs human approval | Blocked for now |
| `destructive` | Can cause outage, data loss, or irreversible change | Disabled and blocked |

## Required Tool Metadata

```json
{
  "name": "get_host_details",
  "display_name": "Get Host Details",
  "domain": "vcenter",
  "category": "Inventory",
  "backend": "pyvmomi",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false,
  "input_schema": {},
  "output_schema": {}
}
```

## Current Execution Rules

```text
read_only -> allowed
low_risk -> TOOL_POLICY_BLOCKED
approval_required -> TOOL_REQUIRES_APPROVAL
destructive -> TOOL_POLICY_BLOCKED
disabled -> TOOL_DISABLED
not implemented -> TOOL_NOT_IMPLEMENTED
```

## Enforcement Points

Policy must be checked in all execution paths:

1. Agent Engine before choosing/executing a tool.
2. FastAPI Tool Gateway before calling infrastructure services.
3. MCP Gateway before calling MCP tools.

Defense in depth is required. If one layer routes incorrectly, the next layer
must still block unsafe execution.

## Hard Blocks

Do not expose or execute:

- Free-form shell commands.
- Raw `govc_command`.
- Kubernetes patch/delete/scale.
- VM delete/destroy.
- Datastore delete/unmount.
- Snapshot delete/revert.
- Host reboot/shutdown/disconnect.
- Any action missing tool metadata.

