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
- [pyVmomi tool registry](docs/knowledge/pyvmomi-tool-registry.md)

## Knowledge Rules

- Do not commit secrets, API keys, kubeconfigs, tokens, passwords, or private SSH keys.
- Store credentials in Kubernetes Secrets or local secure stores only.
- Mark every tool by category and risk level before exposing it to the agent.
- Enable read-only tools first; keep approval-required and destructive tools disabled until the approval workflow exists.

