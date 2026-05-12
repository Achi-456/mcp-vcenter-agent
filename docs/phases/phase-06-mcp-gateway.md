# Phase 6 - MCP Gateway

## Goal

Expose approved tools/resources/prompts through MCP while enforcing the same
tool registry and policy rules used by FastAPI and Agent Engine.

## Planned Work

- Replace MCP placeholder with real MCP-compatible server behavior.
- Expose read-only resources first.
- Expose only safe tool metadata until approval flow exists.
- Route every MCP tool call through PolicyService.

## Boundaries

- No raw shell.
- No raw `govc_command`.
- No destructive MCP tools without approval gate.
- Browser must not call MCP directly.

## Acceptance Criteria

- MCP `/tools`, `/resources`, and `/prompts` reflect platform metadata.
- Unsafe tools are hidden or blocked according to policy.
- MCP server health is included in platform status.

