# Project Knowledge Summary

This file is the short index for durable project knowledge. Detailed knowledge
documents live under `docs/knowledge/`.

## Current Platform

- Project: vCenter Agentic Ops Platform
- Runtime: RKE2 Kubernetes on-premises
- Domain: `dclab.local`
- Active rebuild branch: `rebuild/vcenter-agentic-platform`
- Public UI: `https://infra-agent-console.dclab.local`
- Public API: `https://api.dclab.local`
- Argo CD: `https://argocd-agent.dclab.local`
- Registry: `ghcr.io/achi-456`

## Resources

| VM Name | FQDN | IP | Gateway | DNS |
| --- | --- | ---: | ---: | ---: |
| agentic-cp-01 | agentic-cp-01.dclab.local | 172.25.188.85 | 172.25.188.1 | 172.25.188.20 |
| agentic-worker-01 | agentic-worker-01.dclab.local | 172.25.188.86 | 172.25.188.1 | 172.25.188.20 |
| agentic-worker-02 | agentic-worker-02.dclab.local | 172.25.188.87 | 172.25.188.1 | 172.25.188.20 |
| agentic-db-01 | agentic-db-01.dclab.local | 172.25.188.88 | 172.25.188.1 | 172.25.188.20 |
| agentic-utility-01 | agentic-utility-01.dclab.local | 172.25.188.89 | 172.25.188.1 | 172.25.188.20 |

## Detailed Knowledge

- [Clean rebuild baseline](docs/REBUILD-BASELINE.md)
- [Phase 1.4 migration notes](docs/phase-1-4-migration.md)
- [Current target architecture](docs/knowledge/00-current-target-architecture.md)
- [Agentic flow knowledge](docs/knowledge/agentic-flow-knowledge.md)
- [FastAPI backend architecture](docs/knowledge/fastapi-backend-architecture-knowledge.md)
- [Database architecture](docs/knowledge/database-architecture-knowledge.md)
- [Tool risk policy](docs/knowledge/tool-risk-policy.md)
- [API contract v1](docs/knowledge/api-contract-v1.md)
- [SSE event contract](docs/knowledge/sse-event-contract.md)
- [Validation prompts](docs/knowledge/validation-prompts.md)
- [pyVmomi tool registry](docs/knowledge/vcenter-tools/pyvmomi-tools.md)
- [vCenter tool reference index](docs/knowledge/vcenter-tools/README-vcenter-tool-index.md)

## Knowledge Rules

- Do not commit secrets, API keys, kubeconfigs, tokens, passwords, or private SSH keys.
- Store credentials in Kubernetes Secrets or local secure stores only.
- Mark every tool by category and risk level before exposing it to the agent.
- Enable read-only tools first; keep approval-required and destructive tools disabled until the approval workflow exists.
