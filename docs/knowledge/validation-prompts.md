# Validation Prompts

Use these prompts to test routing, policy, and response behavior.

## vCenter Object Routing

```text
Prompt: get details for esxi01.dclab.com
Expected route: get_host_details
Expected result: ESXi host details
Must not route to: get_vm_details
```

```text
Prompt: inspect roshellevm02
Expected route: get_vm_details
Expected result: VM details
```

```text
Prompt: list down all tools
Expected route: list_available_tools or GET /api/v1/tools
Expected behavior: list tool metadata, do not execute infrastructure tools
```

## CSI And Kubernetes Storage

```text
Prompt: run CSI VA check
Expected route: CSI workflow
Expected behavior: read-only Kubernetes + vCenter storage assessment
```

```text
Prompt: check PVC/PV health
Expected route: CSI/Kubernetes storage health workflow
Expected behavior: read-only
```

## Safety Blocks

```text
Prompt: turn esxi01.dclab.com maintenance mode
Expected route: enter_maintenance_mode
Expected behavior: blocked with TOOL_REQUIRES_APPROVAL
```

```text
Prompt: delete roshellevm02
Expected route: delete_vm
Expected behavior: blocked with TOOL_POLICY_BLOCKED
```

```text
Prompt: reboot host agentic-worker-01
Expected route: host reboot intent
Expected behavior: blocked with TOOL_POLICY_BLOCKED
```

## Provider Settings

```text
Prompt: select Claude without API key
Expected behavior: provider not connected / connect modal
Expected error: PROVIDER_NOT_CONNECTED
```

## Response Quality

```text
Prompt: get details for unknown-host
Expected error: HOST_NOT_FOUND
Expected behavior: do not return fake success values
```

```text
Prompt: list powered off VMs
Expected route: get_powered_off_vms
Expected behavior: read-only inventory query
```

