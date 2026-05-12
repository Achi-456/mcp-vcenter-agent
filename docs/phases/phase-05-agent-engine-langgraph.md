# Phase 5 - Agent Engine LangGraph

## Goal

Move controlled workflow orchestration into Agent Engine with LangGraph while
keeping FastAPI as the only browser-facing gateway.

## Planned Work

- Replace placeholder engine stream with a real LangGraph graph.
- Use official LangGraph Postgres checkpointer tables.
- Keep FastAPI proxy for browser SSE.
- Share tool metadata and policy decisions with the engine.
- Persist session state and run state.

## Boundaries

- Do not duplicate policy enforcement only in the engine; FastAPI must still protect gateway execution paths.
- Do not introduce KEDA until queue-based execution is designed.
- Do not add destructive tools.

## Acceptance Criteria

- Agent Engine `/ready` checks LangGraph, Postgres, and Redis.
- A fixed session ID can resume/checkpoint.
- FastAPI `/api/v1/chat/stream` still works as the public endpoint.

