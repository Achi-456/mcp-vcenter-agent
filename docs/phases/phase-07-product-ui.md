# Phase 7 - Product UI

## Goal

Build the frontend product experience on top of stable backend contracts.

## Planned Work

- Wire chat page to `POST /api/v1/chat/stream`.
- Add tool registry browser using `GET /api/v1/tools`.
- Add health dashboard using `GET /api/v1/health/services`.
- Add session/event rail using SSE events.
- Add quick actions for safe read-only workflows.

## Boundaries

- No raw secrets in browser storage.
- No browser direct calls to Agent Engine or MCP.
- No frontend-only fake infrastructure data once backend endpoints exist.

## Acceptance Criteria

- Chat shows live SSE events and final answer.
- Dashboard reflects backend, Postgres, Redis, vCenter, Agent Engine, and MCP status.
- Tool page clearly shows enabled/implemented/risk status.

