You are working on my AgenticOps vCenter Agentic Ops Platform.

Before coding, read these files:

- AGENTS.md
- knowledge/00-current-target-architecture.md
- knowledge/fastapi-backend-architecture-knowledge.md
- knowledge/database-architecture-knowledge.md
- knowledge/agentic-flow-knowledge.md
- knowledge/tool-risk-policy.md
- knowledge/api-contract-v1.md
- knowledge/sse-event-contract.md
- knowledge/validation-prompts.md
- knowledge/vcenter-tools/(all files)
Do not modify code yet.

Inspect:

- apps/backend
- apps/engine
- apps/frontend only if needed
- k8s manifests
- existing Dockerfiles
- existing CI/CD workflows

Return a discovery report with:

1. Current FastAPI backend structure
2. Existing routers
3. Existing services
4. Existing database/Redis usage
5. Existing settings/secrets flow
6. Existing tool registry implementation
7. Existing audit/session storage if any
8. Existing health endpoints
9. Existing chat/agent stream flow
10. Gaps compared to the knowledge files
11. Minimal implementation plan for Phase 1 FastAPI Foundation Pack
12. Exact files you propose to change
13. Exact files you propose to create
14. Risks before coding
15. Verification commands after coding

Important rules:
- Do not write code.
- Do not rename apps/frontend, apps/backend, or apps/engine.
- Do not replace FastAPI, Next.js, LangGraph, LangChain, Postgres, Redis, Kubernetes, or pyVmomi.
- Do not implement destructive infrastructure actions.
- Do not expose or store secrets.