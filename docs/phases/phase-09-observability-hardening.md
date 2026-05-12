# Phase 9 - Observability And Hardening

## Goal

Harden the platform for operational use with better telemetry, audit review,
deployment safety, and failure visibility.

## Planned Work

- Add OpenTelemetry traces across FastAPI, Engine, MCP, Postgres, Redis, and vCenter calls.
- Add Prometheus metrics.
- Add structured audit review endpoints and UI.
- Add deployment checks for migrations and GitOps sync.
- Add backup/restore notes for Postgres and Redis.

## Boundaries

- Do not add new tool capability in this phase unless needed for observability.
- Do not weaken policy to improve demos.

## Acceptance Criteria

- Failed tool calls and blocked policy decisions are traceable.
- Audit events can be searched and exported.
- Cluster rollout failures have documented triage commands.

