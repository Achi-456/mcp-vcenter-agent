# Phase 2 - vCenter Read-Only Tools

## Goal

Implement real read-only vCenter inventory and context tools behind the Phase 1
registry and policy foundation.

## Planned Work

- Add pyVmomi connection factory using Kubernetes Secret reference.
- Add read-only services for VMs, hosts, datastores, clusters, networks, alarms, and events.
- Implement these registry tools:
  - `get_environment_overview`
  - `list_vms`
  - `get_vm_details`
  - `list_hosts`
  - `get_host_details`
  - `list_datastores`
  - `get_datastore_health`
  - `get_active_alarms`
  - `get_recent_events`
- Mark only completed tools as `implemented=true`.
- Add Redis caching with `refresh=true` bypass.
- Add audit events for each read-only tool call.

## Boundaries

- No VM power actions.
- No snapshots.
- No host maintenance mode.
- No raw `govc_command`.
- No destructive or approval-required execution.

## Acceptance Criteria

- `get details for esxi01.dclab.com` routes to host details, not VM details.
- `inspect roshellevm02` routes to VM details.
- Unknown objects return `HOST_NOT_FOUND`, `VM_NOT_FOUND`, or `WRONG_OBJECT_TYPE`.
- Failed vCenter auth/session errors are not cached.

