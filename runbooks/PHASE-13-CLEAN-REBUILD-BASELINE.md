# Phase 13 - Clean Rebuild Baseline

## Summary

This phase intentionally resets the broken application layer to a minimal,
buildable baseline. It preserves the repo, GitOps manifests, and CI structure,
but replaces the product code under `apps/` with small service boundaries that
can be rebuilt safely.

## Scope

- Next.js frontend shell with `/` and `/chat`.
- FastAPI backend with `/health`, `/ready`, `/api/v1/platform/status`,
  `/api/v1/agent/run`, `/api/v1/chat/stream`, and `/ws`.
- Agent engine placeholder with `/health`, `/ready`, `/run`, and
  `/sessions/{session_id}`.
- MCP placeholder with `/health`, `/tools`, `/resources`, and `/prompts`.
- Dockerfiles and `.dockerignore` files for all four services.

## Non-Goals

- No vCenter credentials.
- No LLM API keys.
- No real LangGraph checkpointer.
- No Postgres or Redis dependency from `/health`.
- No MCP SDK tool execution.
- No Kubernetes secret changes.

## Local Validation

```powershell
cd apps/frontend
npm ci
npm audit --audit-level=moderate
npm run build
cd ..\..

docker build -t agentic-fastapi:rebuild apps/backend
docker build -t agentic-nextjs:rebuild apps/frontend
docker build -t agentic-engine:rebuild apps/engine
docker build -t agentic-mcp:rebuild apps/mcp
```

## Rebuild Order After This Phase

1. Wire frontend chat to backend SSE.
2. Wire backend to internal agent-engine service.
3. Reintroduce LangGraph with Postgres and Redis readiness checks.
4. Add encrypted provider settings and admin login.
5. Add read-only vCenter inventory.
6. Add MCP protocol implementation and read-only tools.

