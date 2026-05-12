# Rebuild Phase Tracker

This folder tracks leftovers, handoff notes, and future work for the clean
rebuild. It is separate from `runbooks/`, which document operational execution,
and from `docs/knowledge/`, which documents architecture and policy.

Use these files before starting a phase:

1. Read the current phase file.
2. Check the previous phase's leftover section.
3. Confirm assumptions against the real repo and cluster.
4. Move completed items into the phase result notes after implementation.

## Phase Index

| Phase | File | Purpose |
| --- | --- | --- |
| Phase 1 | `phase-01-fastapi-foundation.md` | FastAPI foundation, DB/Redis/Secrets, registry, policy, audit |
| Phase 2 | `phase-02-vcenter-readonly-tools.md` | Real pyVmomi read-only inventory and context tools |
| Phase 3 | `phase-03-chat-agent-routing.md` | Chat routing, intent detection, policy-aware tool selection |
| Phase 4 | `phase-04-csi-va-check.md` | Kubernetes CSI validation assessment workflow |
| Phase 5 | `phase-05-agent-engine-langgraph.md` | LangGraph agent workflow and checkpoint integration |
| Phase 6 | `phase-06-mcp-gateway.md` | MCP gateway, tool/resource/prompt exposure with policy checks |
| Phase 7 | `phase-07-product-ui.md` | Frontend product UI wired to stable backend contracts |
| Phase 8 | `phase-08-approval-workflow.md` | Human approval workflow for non-read-only operations |
| Phase 9 | `phase-09-observability-hardening.md` | Audit, metrics, traces, logs, deployment hardening |

