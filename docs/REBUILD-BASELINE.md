# Clean Rebuild Baseline

This branch intentionally removes the broken product implementation and replaces
it with a minimal, buildable scaffold for the four service boundaries:

- `apps/frontend` - Next.js console shell and chat placeholder
- `apps/backend` - FastAPI gateway with health, readiness, SSE placeholder, and WebSocket echo
- `apps/engine` - FastAPI agent-engine placeholder with SSE-compatible events
- `apps/mcp` - FastAPI MCP placeholder exposing empty tools/resources/prompts

The goal is to restore a known-good base before reintroducing inventory, LLM
providers, LangGraph checkpoints, MCP tool execution, and vCenter credentials.

## Rules for the Rebuild

- Do not commit secrets, kubeconfigs, API keys, or vCenter credentials.
- Keep Docker builds passing before adding feature code.
- Keep GitHub Actions paths aligned with real app directories.
- Reintroduce features in small phases with local build validation first.
- Do not use `latest` image tags in Kubernetes manifests.

## Suggested Next Phases

1. Reconnect frontend chat to backend SSE.
2. Add backend-to-engine proxy with internal service URL.
3. Add LangGraph skeleton and Postgres/Redis readiness checks.
4. Add encrypted provider settings and admin login.
5. Add read-only vCenter inventory.
6. Add MCP protocol implementation and read-only tools.

