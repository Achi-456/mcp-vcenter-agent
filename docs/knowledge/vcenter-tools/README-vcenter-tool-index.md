# vCenter Tool Integration Index

This folder contains separate Markdown files for the main vCenter integration layers you can connect to the MCP server and Agent Engine.

## Files

1. `pyvmomi-tools.md`
   - Primary Python vCenter integration layer.
   - Best for FastAPI backend and current production tools.
   - Inventory, VM/host/datastore, alarms, events.

2. `govmomi-tools.md`
   - Go SDK for deep vSphere automation and CNS/CSI integration.
   - Best as a separate Go microservice or dedicated MCP server.
   - Strong for CNS volume mapping, SPBM/PBM, and CSI VA checks.

3. `govc-readonly-tools.md`
   - CLI fallback/debug layer.
   - Must be read-only and whitelisted.
   - Useful for VM info, host info, datastore info, events, and CNS volume list.

4. `vsphere-rest-api-tools.md`
   - REST / Automation API layer.
   - Best for tags, content library, vCenter appliance, task summaries, and lightweight object summaries.

## Recommended priority

```text
Current:
1. pyVmomi

Next:
2. govc read-only fallback
3. vSphere REST API tags/content library/tasks
4. govmomi CNS microservice for CSI/CNS

Later:
5. PowerCLI / Ansible / Terraform with approval workflow
```

## Global safety rule

Every tool must have metadata:

```json
{
  "risk_level": "read_only | low_risk | approval_required | destructive",
  "enabled": true,
  "implemented": true,
  "requires_approval": false
}
```

In the current phase:

```text
Only read_only tools should execute automatically.
All approval_required/destructive tools must be blocked.
```
