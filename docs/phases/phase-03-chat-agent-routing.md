# Phase 3 - Chat Agent Routing

## Goal

Connect chat prompts to intent detection, tool selection, policy checks, audit,
and SSE events while keeping the browser-facing API stable.

## Planned Work

- Keep `POST /api/v1/chat/stream` as the public chat endpoint.
- Emit the documented SSE contract from `docs/knowledge/sse-event-contract.md`.
- Add routing for validation prompts:
  - list tools
  - host details
  - VM details
  - powered-off VMs
  - blocked maintenance/delete/reboot requests
- Use ToolRegistryService and PolicyService before any tool call.
- Audit allowed and blocked tool decisions.
- Keep Agent Engine optional until Phase 5 if direct backend routing is simpler for read-only tools.

## Boundaries

- No public tool execution endpoint.
- No frontend direct calls to Agent Engine or MCP.
- No destructive tool execution.

## Acceptance Criteria

- `list down all tools` lists metadata only.
- `turn esxi01.dclab.com maintenance mode` is blocked with `TOOL_REQUIRES_APPROVAL`.
- `delete roshellevm02` is blocked with `TOOL_POLICY_BLOCKED`.
- SSE emits `start`, intent/policy/tool/final events, then `done`.

