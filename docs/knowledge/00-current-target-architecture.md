# Current Target Architecture

This file freezes the target architecture for the current rebuild so coding
work does not drift across frameworks, folders, or runtime models.

## Service Boundaries

```text
Frontend:     apps/frontend
Backend:      apps/backend
Agent Engine: apps/engine
MCP Server:   apps/mcp
Knowledge:    docs/knowledge
Kubernetes:   k8s
Runbooks:     runbooks
```

## Runtime Model

```text
Next.js Frontend
  -> FastAPI Backend
  -> Agent Engine / MCP / vCenter / Kubernetes / Postgres / Redis
```

Rules:

- FastAPI is the only browser-facing API gateway.
- Browser must not call Agent Engine or MCP directly.
- LangGraph controls workflow orchestration.
- LangChain is used inside nodes for prompts, parsers, LLM calls, and tool wrappers.
- MCP exposes external tools only through policy-controlled gateways.
- Postgres stores durable platform state, metadata, checkpoints, audit, reports, and sessions.
- Redis stores short-lived cache, temporary run state, and future queue state.
- Kubernetes Secrets store actual sensitive credentials.
- Only `read_only` tools execute automatically.
- `low_risk`, `approval_required`, and `destructive` tools are blocked until the approval workflow exists.

## First Coding Milestone

Milestone 1 is:

```text
Backend foundation + database + tool registry + policy enforcement
```

Order:

1. Backend folder cleanup.
2. Database models and migrations.
3. Redis cache service.
4. Kubernetes Secret reference model.
5. Tool registry v2.
6. Policy service.
7. Audit logging.
8. Health endpoints.

Out of scope for Milestone 1:

- Real multi-agent behavior.
- Destructive vCenter or Kubernetes actions.
- Raw `govc_command` execution.
- Direct browser access to Agent Engine or MCP.
- Storing secrets in Postgres.

