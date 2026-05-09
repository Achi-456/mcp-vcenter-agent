# agent.md — vCenter Agentic Ops Platform

> **Purpose:** This file is the single source of truth for AI-assisted development (vibe coding) of the vCenter Agentic Ops Platform. Paste this into any AI coding session. Every architectural decision, stack choice, cluster detail, deployment step, and coding convention is documented here. The AI should never guess — refer here first.

---

## 1. Project Identity

| Field | Value |
|---|---|
| Project name | vCenter Agentic Ops Platform |
| Purpose | AI-powered VMware vCenter admin agent — query, diagnose, and safely operate vCenter infrastructure via natural language |
| Primary language | Python 3.12 (backend) · TypeScript (frontend) |
| Repo structure | monorepo — `apps/backend/` and `apps/frontend/` |
| Environment | Kubernetes (RKE2) on-premises — `dclab.local` domain |
| Current phase | v0.1 — scaffold and clean |

---

## 2. Cluster — Nodes and IPs

| VM Name | FQDN | IP | Role | vCPU | RAM | Disk |
|---|---|---|---|---|---|---|
| agentic-cp-01 | agentic-cp-01.dclab.local | 172.25.188.85 | RKE2 Control Plane | 2 | 8 GB | 100 GB sda |
| agentic-worker-01 | agentic-worker-01.dclab.local | 172.25.188.86 | App / Frontend | 4 | 12 GB | 150 GB sda |
| agentic-worker-02 | agentic-worker-02.dclab.local | 172.25.188.87 | Agent Engine | 4 | 12 GB | 150 GB sda |
| agentic-db-01 | agentic-db-01.dclab.local | 172.25.188.88 | Postgres / Redis / VectorDB | 4 | 16 GB | 100 GB sda + 300 GB sdb → /data |
| agentic-utility-01 | agentic-utility-01.dclab.local | 172.25.188.89 | Argo CD / Monitoring | 2 | 6 GB | 80 GB sda |

### Node labels (applied during RKE2 join)
```
agentic-cp-01      → taint: CriticalAddonsOnly=true:NoExecute
agentic-worker-01  → label: role=app-worker
agentic-worker-02  → label: role=app-worker
agentic-db-01      → label: role=data
agentic-utility-01 → label: role=utility
```

### Namespace map
| Namespace | Node affinity | Contents |
|---|---|---|
| `agentic-app` | worker-01 | Next.js, FastAPI, MCP server |
| `agentic-agents` | worker-02 | LangGraph agent pods |
| `agentic-data` | db-01 | Postgres, Redis |
| `argocd` | utility-01 | Argo CD |
| `monitoring` | utility-01 | Prometheus, Grafana |
| `longhorn-system` | db-01 | Longhorn storage |
| `cert-manager` | utility-01 | cert-manager |

---

## 3. Full Technology Stack

### Backend
| Layer | Technology | Why |
|---|---|---|
| API framework | FastAPI | async, SSE streaming, OpenAPI auto-docs |
| Agent orchestration | LangGraph | durable execution, graph state, human-in-the-loop, checkpoints, resumable workflows |
| Tool / model layer | LangChain | tool definitions, middleware, model integrations, context compression |
| vCenter SDK | pyVmomi | VMware official Python SDK for vCenter API |
| CLI tool | govc | faster batch vCenter operations via CLI |
| Web search | Tavily | agent-callable web search for VMware KB |
| External tool protocol | MCP (Model Context Protocol) | expose vCenter tools/resources/prompts to models |
| LLM providers | Anthropic Claude (primary) · OpenAI (fallback) · Google Gemini (fallback) |
| Database ORM | SQLAlchemy + Alembic | migrations, async sessions |
| Task queue / cache | Redis | tool result cache, rate limiting, pub/sub for WebSocket events |
| Persistence | Postgres 16 + pgvector | sessions, audit log, approvals, LangGraph checkpointer, vector embeddings |
| Agent observability | LangSmith | agent trace debugging and evals |
| Tracing | OpenTelemetry | distributed traces across all pods |

### Frontend
| Layer | Technology | Why |
|---|---|---|
| Framework | Next.js 15 (App Router) + TypeScript | SSR, strong typing, file-based routing |
| UI components | shadcn/ui + Tailwind CSS | accessible, unstyled-first, fully customisable |
| Server state | TanStack Query v5 | caching, background refetch, optimistic updates |
| Tables | TanStack Table v8 | virtualised, sortable, filterable VM/host inventory tables |
| Charts | Recharts | resource usage graphs, agent activity timelines |
| Realtime | Server-Sent Events (SSE) for agent token stream · WebSocket for inventory push |

### Infrastructure
| Layer | Technology |
|---|---|
| Kubernetes distribution | RKE2 (Rancher Kubernetes Engine 2) |
| Container runtime | containerd (bundled with RKE2) |
| CNI | Canal (Flannel + Calico) — bundled with RKE2 |
| Ingress | Traefik — bundled with RKE2 |
| Storage | Longhorn — block storage, PVCs backed by /data on db-01 |
| TLS | cert-manager + self-signed ClusterIssuer for dclab.local |
| GitOps | Argo CD on utility-01 |
| Monitoring | kube-prometheus-stack (Prometheus + Grafana) |
| Image registry | ghcr.io or local Harbor (future) |

---

## 4. Repository Structure

```
vcenter-agentic-platform/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── main.py                  # FastAPI app entry point
│   │   │   │   └── routes/
│   │   │   │       ├── chat.py              # POST /chat → SSE stream
│   │   │   │       ├── sessions.py          # session CRUD
│   │   │   │       ├── approvals.py         # human approval pause/resume
│   │   │   │       ├── tools.py             # tool registry endpoints
│   │   │   │       └── inventory.py         # vCenter inventory read endpoints
│   │   │   │
│   │   │   ├── agents/
│   │   │   │   ├── graph.py                 # LangGraph StateGraph definition
│   │   │   │   ├── state.py                 # AgentState TypedDict
│   │   │   │   ├── supervisor.py            # supervisor node — routes to specialists
│   │   │   │   ├── planner_agent.py         # produces structured JSON plan
│   │   │   │   ├── inventory_agent.py       # read-only vCenter discovery
│   │   │   │   ├── operation_agent.py       # mutation operations (with safety gate)
│   │   │   │   ├── safety_agent.py          # risk classification + approval trigger
│   │   │   │   ├── reviewer_agent.py        # validates agent output quality
│   │   │   │   ├── reporter_agent.py        # structured final report
│   │   │   │   └── memory_agent.py          # memory read/write coordination
│   │   │   │
│   │   │   ├── tools/
│   │   │   │   ├── registry/
│   │   │   │   │   ├── base.py              # ToolSpec dataclass, RiskLevel enum
│   │   │   │   │   ├── manifest.py          # all tool registrations
│   │   │   │   │   ├── loader.py            # versioned tool loader
│   │   │   │   │   └── permissions.py       # allowlist / denylist
│   │   │   │   ├── vcenter/
│   │   │   │   │   ├── inventory_tools.py   # list_vms, get_vm_details, list_hosts...
│   │   │   │   │   ├── vm_power_tools.py    # power_on, power_off, reboot
│   │   │   │   │   ├── snapshot_tools.py    # create, list, revert, delete snapshot
│   │   │   │   │   ├── host_tools.py        # maintenance mode, host details
│   │   │   │   │   └── datastore_tools.py   # list, usage, browse
│   │   │   │   ├── govc/
│   │   │   │   │   └── govc_tool.py         # subprocess govc wrapper
│   │   │   │   ├── search/
│   │   │   │   │   └── web_search_tool.py   # Tavily search
│   │   │   │   └── mcp/
│   │   │   │       └── mcp_client_tools.py  # MCP client bridge
│   │   │   │
│   │   │   ├── memory/
│   │   │   │   ├── short_term.py            # working memory in graph state
│   │   │   │   ├── entity_store.py          # persistent VM/host/datastore entity cache
│   │   │   │   ├── session_store.py         # session CRUD (Postgres)
│   │   │   │   ├── semantic_store.py        # pgvector embedding store
│   │   │   │   ├── summarizer.py            # rolling LLM summary compression
│   │   │   │   └── long_term.py             # RAG retrieval from semantic store
│   │   │   │
│   │   │   ├── context/
│   │   │   │   ├── budget.py                # ContextBudgetManager — token tracking
│   │   │   │   ├── compression.py           # message trimming, summary injection
│   │   │   │   ├── prompt_builder.py        # assembles final context each turn
│   │   │   │   ├── retrieval.py             # semantic memory retrieval
│   │   │   │   └── redaction.py             # strips secrets from tool results
│   │   │   │
│   │   │   ├── safety/
│   │   │   │   ├── policy.py                # RiskLevel definitions and rules
│   │   │   │   ├── approvals.py             # approval record CRUD
│   │   │   │   ├── risk_classifier.py       # classifies tool call risk
│   │   │   │   ├── audit.py                 # writes immutable audit log rows
│   │   │   │   └── dry_run.py               # dry-run preview generation
│   │   │   │
│   │   │   ├── llm/
│   │   │   │   ├── providers/
│   │   │   │   │   ├── anthropic_provider.py
│   │   │   │   │   ├── openai_provider.py
│   │   │   │   │   └── gemini_provider.py
│   │   │   │   ├── model_router.py          # failover: Anthropic → OpenAI → Gemini
│   │   │   │   └── cost_tracker.py          # per-session token + cost accounting
│   │   │   │
│   │   │   ├── workflows/
│   │   │   │   ├── vm_health_check.py
│   │   │   │   ├── vm_snapshot_workflow.py
│   │   │   │   ├── host_maintenance_workflow.py
│   │   │   │   ├── migration_workflow.py
│   │   │   │   └── incident_triage_workflow.py
│   │   │   │
│   │   │   ├── observability/
│   │   │   │   ├── tracing.py               # OpenTelemetry setup
│   │   │   │   ├── metrics.py               # Prometheus metrics
│   │   │   │   └── logs.py                  # structlog JSON logging
│   │   │   │
│   │   │   └── db/
│   │   │       ├── models.py                # SQLAlchemy ORM models
│   │   │       └── migrations/              # Alembic migrations
│   │   │
│   │   ├── mcp/
│   │   │   └── server.py                    # MCP server exposing vCenter tools/resources
│   │   │
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── frontend/
│       ├── app/                             # Next.js App Router pages
│       │   ├── page.tsx                     # dashboard home
│       │   ├── chat/page.tsx                # agent chat interface
│       │   ├── inventory/page.tsx           # VM / host / datastore tables
│       │   ├── approvals/page.tsx           # pending approval cards
│       │   ├── sessions/page.tsx            # session history
│       │   └── tools/page.tsx               # tool registry browser
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatWindow.tsx           # SSE stream renderer
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── ToolCallCard.tsx         # shows tool name + args + result
│       │   │   └── ApprovalDialog.tsx       # shadcn AlertDialog for approval flow
│       │   ├── inventory/
│       │   │   ├── VMTable.tsx              # TanStack Table — VM list
│       │   │   ├── HostTable.tsx
│       │   │   └── DatastoreTable.tsx
│       │   └── charts/
│       │       ├── ResourceGauge.tsx        # Recharts — CPU/RAM gauges
│       │       └── AgentTimeline.tsx        # Recharts — agent step timeline
│       ├── lib/
│       │   ├── api.ts                       # TanStack Query hooks
│       │   ├── websocket.ts                 # WebSocket client for inventory push
│       │   └── sse.ts                       # SSE client for agent stream
│       ├── Dockerfile
│       ├── next.config.ts
│       └── package.json
│
├── k8s/
│   ├── namespaces.yaml
│   ├── apps/
│   │   ├── fastapi/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── ingress.yaml                # api.dclab.local
│   │   ├── nextjs/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── ingress.yaml                # app.dclab.local
│   │   ├── agents/
│   │   │   ├── deployment.yaml             # nodeSelector: role=app-worker (worker-02)
│   │   │   └── hpa.yaml                    # min:1 max:4 cpu:60%
│   │   ├── mcp/
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   └── data/
│   │       ├── postgres-values.yaml        # Helm values
│   │       └── redis-values.yaml
│   └── secrets/
│       └── agentic-secrets.yaml.example    # never commit real secrets
│
├── docs/
│   ├── architecture.md
│   ├── agent.md                            # ← this file
│   ├── tool-authoring-guide.md
│   ├── safety-policy.md
│   └── version-roadmap.md
│
└── tests/
    ├── unit/
    ├── integration/
    └── evals/
```

---

## 5. LangGraph Agent Design

### Graph flow
```
START
  ↓
load_context          ← inject memory, entity cache, rolling summary
  ↓
supervisor            ← routes to planner or directly to specialist
  ↓
planner               ← produces structured JSON step plan
  ↓
risk_classifier       ← assigns RiskLevel to each plan step
  ↓
approval_required?
  ├─ YES → interrupt_before → WebSocket push "approval_required"
  │         → UI shows ApprovalDialog → POST /approvals/:id
  │         → graph.update_state() → resume
  └─ NO  ↓
select_agent
  ↓
inventory_agent / operation_agent / docs_agent
  ↓
update_memory         ← write entity cache, session store
  ↓
reviewer              ← validates output quality
  ↓
needs_more_work?
  ├─ YES → supervisor  (max 3 nudges before escalate)
  └─ NO  ↓
reporter              ← structured final answer + audit record
  ↓
END
```

### AgentState (state.py)
```python
class AgentState(TypedDict):
    session_id: str
    user_message: str
    system_prompt: str
    messages: list[NormalizedMessage]
    plan: dict | None                        # structured planner output
    current_step: dict | None
    risk: str | None                         # RiskLevel value
    approval: dict | None                    # pending approval record
    tool_results: list[dict]
    tool_cache: dict[str, str]               # cache_key → JSON result
    tool_version: str                        # "v1" | "v2" | "latest"
    known_entities: dict                     # {vms, hosts, datastores, clusters}
    rolling_summary: str                     # compressed earlier turns
    turns_since_summary: int
    memory_refs: list[str]                   # semantic memory hit IDs
    cost: dict                               # {input_tokens, output_tokens, usd}
    errors: list[str]
    reflection_verdict: str | None           # COMPLETE | NEEDS_MORE_TOOLS | NEEDS_HUMAN
    reflection_nudges_used: int
    final_answer: str | None
    next_node: str                           # explicit routing override
```

### Planner output schema
```json
{
  "goal": "string",
  "risk": "READ_ONLY | LOW_RISK | MEDIUM_RISK | HIGH_RISK | CRITICAL",
  "steps": [
    {
      "id": "string",
      "agent": "inventory | operation | docs",
      "tool": "tool_name",
      "reason": "string"
    }
  ]
}
```

### Risk levels
| Level | Examples | Requires approval |
|---|---|---|
| READ_ONLY | list_vms, get_vm_details, get_events | No |
| LOW_RISK | create_snapshot | No |
| MEDIUM_RISK | power_off_vm, reboot_guest | Yes |
| HIGH_RISK | delete_vm, migrate_vm, enter_maintenance_mode | Yes |
| CRITICAL | delete_datastore, mass_power_off, destructive govc | Yes + confirmation |

---

## 6. Tool Design

### ToolSpec (registry/base.py)
```python
@dataclass
class ToolSpec:
    name: str                    # format: "vcenter.vm.power_off"
    version: str                 # semver: "1.0.0"
    description: str
    input_schema: dict           # JSON Schema
    output_schema: dict          # JSON Schema
    risk_level: str              # RiskLevel enum value
    read_only: bool
    requires_approval: bool
    timeout_seconds: int
    owner: str                   # "vcenter" | "govc" | "search" | "mcp"
    tags: list[str]
```

### Tool naming convention
```
vcenter.vm.get_details@1.0.0
vcenter.vm.power_off@1.0.0
vcenter.vm.power_off@1.1.0
vcenter.snapshot.create@1.0.0
vcenter.host.enter_maintenance@1.0.0
govc.run_command@1.0.0
search.web@1.0.0
```

### Timeout rules
| Tool type | Timeout |
|---|---|
| Read-only vCenter | 10–30 s |
| govc commands | 30–120 s |
| Mutation tools | 120–600 s |

### Concurrency rules
| Operation type | Concurrency |
|---|---|
| Read-only inventory | Parallel allowed |
| Mutation per VM | Serial |
| Mutation per host | Serial |
| govc command | Restricted serial (1 at a time) |

---

## 7. Memory Architecture

### Four tiers
| Tier | Scope | Storage | Contents |
|---|---|---|---|
| Working memory | Current graph state (in-turn) | RAM / AgentState | plan, tool results, pending approval, errors |
| Entity memory | Cross-turn persistent | Postgres `entity_cache` table | VM name, MOID, host, datastore, power state, last_seen, confidence |
| Session memory | Per-session | Postgres `sessions` table | objective, summary, actions_taken, tool_evidence, open_questions |
| Long-term semantic | Cross-session | Postgres + pgvector | runbooks, VMware KB summaries, past troubleshooting cases, SOPs |

### Entity memory schema
```
vm_name        TEXT
moid           TEXT PRIMARY KEY
host           TEXT
datastore      TEXT
power_state    TEXT
last_seen      TIMESTAMP
confidence     FLOAT
source_tool    TEXT
session_id     TEXT
```

### Rolling summary trigger
- Compress when `turns_since_summary >= AGENT_SUMMARIZE_EVERY` (default: 5)
- Summariser sends last N turns to LLM → returns compressed paragraph
- Summary replaces those turns in the context window
- `turns_since_summary` resets to 0

---

## 8. Context Window Management

### ContextBudgetManager budget allocation
```
System prompt + safety policies   15%
Current task + active plan        15%
Recent conversation (last 3–5)    20%
Tool evidence (latest results)    25%
Memory / RAG retrieved context    15%
Reserve for model output          10%
```

### Context assembly order (prompt_builder.py)
```python
def build_context(state, max_tokens):
    return {
        "system":           system_prompt + safety_policy,
        "task":             state["user_message"],
        "plan":             compressed_plan(state["plan"]),
        "recent_messages":  last_n_messages(state["messages"], n=5),
        "entity_context":   format_entity_cache(state["known_entities"]),
        "retrieved_memory": semantic_search(state["user_message"]),
        "tool_evidence":    latest_tool_results(state["tool_results"]),
        "summary":          state["rolling_summary"],
    }
```

### Tool result compression rule
Large vCenter responses (e.g. full VM list of 500 VMs) must be compressed before entering context:
- Full result → stored in Postgres + Redis cache
- Model context → receives only: count, top N relevant VMs, matched names

---

## 9. Realtime Architecture

### Agent token stream (SSE)
```
User POST /api/v1/chat
  → FastAPI creates session
  → calls LangGraph graph.astream()
  → yields token events as SSE
  → Next.js EventSource receives tokens
  → ChatWindow.tsx appends to message buffer
```

### Inventory push (WebSocket)
```
vCenter tool returns result
  → FastAPI publishes to Redis pub/sub channel "inventory:{session_id}"
  → WebSocket handler subscribes and forwards to browser
  → TanStack Table row updates live
  → Recharts chart updates live
```

### Approval flow
```
Safety agent classifies HIGH_RISK
  → LangGraph interrupt_before(node="operation_agent")
  → FastAPI writes approval record to Postgres
  → WebSocket pushes {type:"approval_required", approval_id, details} to browser
  → ApprovalDialog.tsx opens (shadcn AlertDialog)
  → Shows dry-run preview (VM name, action, before-state)
  → User clicks Approve / Edit / Reject
  → POST /api/v1/approvals/{id}
  → FastAPI calls graph.update_state({"approval": result})
  → graph.invoke() resumes from checkpoint
```

---

## 10. MCP Server Design

The MCP server (`apps/backend/mcp/server.py`) exposes three categories:

### MCP Tools (executable)
```
vcenter.vm.power_on
vcenter.vm.power_off
vcenter.vm.snapshot_create
vcenter.host.enter_maintenance
```

### MCP Resources (read-only context)
```
vcenter://inventory/vms
vcenter://inventory/hosts
vcenter://inventory/datastores
vcenter://alarms/active
vcenter://events/recent
```

### MCP Prompts (reusable workflows)
```
troubleshoot-vm
prepare-maintenance-mode
safe-poweroff-checklist
vm-migration-checklist
```

**Rule:** Never expose HIGH_RISK or CRITICAL tools via MCP without an approval gate in the tool handler.

---

## 11. Kubernetes Deployment Details

### All nodeSelectors
Every workload must have an explicit `nodeSelector` — never allow a pod to land on cp-01.

```yaml
# worker-01 workloads (Next.js, FastAPI, MCP)
nodeSelector:
  role: app-worker
  kubernetes.io/hostname: agentic-worker-01.dclab.local

# worker-02 workloads (LangGraph agents)
nodeSelector:
  role: app-worker
  kubernetes.io/hostname: agentic-worker-02.dclab.local

# db-01 workloads (Postgres, Redis)
nodeSelector:
  role: data

# utility-01 workloads (Argo CD, Prometheus, Grafana)
nodeSelector:
  role: utility
```

### Resource limits — all pods
| Pod | CPU request | CPU limit | Memory request | Memory limit |
|---|---|---|---|---|
| Next.js | 250m | 1000m | 256Mi | 1Gi |
| FastAPI | 250m | 1000m | 256Mi | 2Gi |
| MCP server | 100m | 500m | 128Mi | 512Mi |
| Agent pod | 500m | 2000m | 1Gi | 4Gi |
| Postgres | 1000m | 3000m | 2Gi | 10Gi |
| Redis | 250m | 1000m | 512Mi | 2Gi |

### HPA (agent pods)
```yaml
minReplicas: 1
maxReplicas: 4
targetCPUUtilizationPercentage: 60
```

### Ingress hostnames
| Service | Hostname | Node |
|---|---|---|
| Next.js UI | app.dclab.local | worker-01 |
| FastAPI | api.dclab.local | worker-01 |
| Argo CD | argocd.dclab.local | utility-01 |
| Grafana | grafana.dclab.local | utility-01 |
| Longhorn UI | longhorn.dclab.local | utility-01 |

### Secrets — never hardcode, always K8s Secret
```bash
kubectl create secret generic agentic-secrets -n agentic-app \
  --from-literal=ANTHROPIC_API_KEY=... \
  --from-literal=OPENAI_API_KEY=... \
  --from-literal=VCENTER_HOST=... \
  --from-literal=VCENTER_USER=... \
  --from-literal=VCENTER_PASSWORD=... \
  --from-literal=DB_URL=postgresql://postgres:pw@postgres.agentic-data.svc:5432/agentic \
  --from-literal=REDIS_URL=redis://:pw@redis-master.agentic-data.svc:6379
```

---

## 12. Postgres Schema (key tables)

```sql
-- Sessions
CREATE TABLE sessions (
    session_id    TEXT PRIMARY KEY,
    user_id       TEXT,
    vcenter_host  TEXT,
    objective     TEXT,
    summary       TEXT,
    actions_taken JSONB,
    tool_evidence JSONB,
    open_questions TEXT[],
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Entity cache
CREATE TABLE entity_cache (
    moid          TEXT PRIMARY KEY,
    vm_name       TEXT,
    host          TEXT,
    datastore     TEXT,
    power_state   TEXT,
    last_seen     TIMESTAMPTZ,
    confidence    FLOAT,
    source_tool   TEXT,
    session_id    TEXT
);

-- Audit log (append-only)
CREATE TABLE audit_log (
    id            BIGSERIAL PRIMARY KEY,
    session_id    TEXT,
    user_id       TEXT,
    tool_name     TEXT,
    tool_version  TEXT,
    input_args    JSONB,
    risk_level    TEXT,
    approval_id   TEXT,
    before_state  JSONB,
    after_state   JSONB,
    tool_output   JSONB,
    model_used    TEXT,
    timestamp     TIMESTAMPTZ DEFAULT now()
);

-- Approvals
CREATE TABLE approvals (
    id            TEXT PRIMARY KEY,
    session_id    TEXT,
    tool_name     TEXT,
    tool_args     JSONB,
    risk_level    TEXT,
    dry_run       JSONB,
    status        TEXT DEFAULT 'pending',  -- pending | approved | edited | rejected
    edited_args   JSONB,
    decided_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Semantic memory (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE memory_embeddings (
    id            BIGSERIAL PRIMARY KEY,
    session_id    TEXT,
    content       TEXT,
    embedding     vector(1536),
    metadata      JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON memory_embeddings USING hnsw (embedding vector_cosine_ops);
```

---

## 13. Backend Environment Variables

```env
# LLM providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
DEFAULT_MODEL=claude-sonnet-4-20250514
FALLBACK_MODEL=gpt-4o

# vCenter
VCENTER_HOST=
VCENTER_PORT=443
VCENTER_USER=
VCENTER_PASSWORD=
VCENTER_IGNORE_SSL=false

# Database
DB_URL=postgresql+asyncpg://postgres:pw@postgres.agentic-data.svc:5432/agentic
REDIS_URL=redis://:pw@redis-master.agentic-data.svc:6379

# Agent behaviour
AGENT_MAX_TURNS=20
AGENT_SUMMARIZE_EVERY=5
AGENT_TOOL_TIMEOUT_READ=30
AGENT_TOOL_TIMEOUT_MUTATE=300
AGENT_MAX_PARALLEL_TOOLS=3

# Context
CONTEXT_MAX_TOKENS=150000
CONTEXT_RESERVE_OUTPUT=0.10

# Observability
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=vcenter-agent
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.monitoring.svc:4317

# App
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=
```

---

## 14. Frontend Environment Variables

```env
NEXT_PUBLIC_API_URL=https://api.dclab.local
NEXT_PUBLIC_WS_URL=wss://api.dclab.local/ws
NEXT_PUBLIC_APP_NAME=vCenter Agentic Ops
```

---

## 15. Version Roadmap

| Version | Goal | Key deliverables |
|---|---|---|
| **v0.1** | Clean + scaffold | Remove .env from git, split routes, pyproject.toml, ruff/mypy, Next.js stub replaces NiceGUI, Argo CD wired |
| **v0.2** | Tool registry | ToolSpec, RiskLevel, versioned tools, tool audit log, `/tools` API, TanStack Table tool browser |
| **v0.3** | LangGraph single agent | Replace engine.py with graph.py, SSE streaming to React, SQLite → Postgres checkpointer, session resume |
| **v0.4** | Human approval UI | LangGraph interrupt, WebSocket push, shadcn ApprovalDialog, dry-run preview, approve/edit/reject |
| **v0.5** | Multi-agent graph | Supervisor + 6 specialist agents, worker-02 dedicated pods, HPA, agent activity Recharts timeline |
| **v0.6** | Long-term memory + RAG | pgvector, runbook ingestion, session similarity search, memory timeline UI |
| **v0.7** | Observability | OpenTelemetry, LangSmith, Prometheus metrics, Grafana agent dashboard, Redis rate limiting |
| **v1.0** | Production | RBAC + SSO, full audit log, backup/restore, least-privilege vCenter account guide, eval tests |

---

## 16. Coding Conventions

### Python (backend)
- Python 3.12, strict type hints everywhere
- `async/await` throughout — no blocking calls in async context
- `pydantic` for all request/response models
- `structlog` for JSON logging — no `print()` statements
- `ruff` for linting, `mypy` for type checking
- All tool functions must return `ToolExecutionResult` — never raise uncaught exceptions
- Every database operation goes through SQLAlchemy async session
- Never commit secrets — use K8s Secrets mounted as env vars

### TypeScript (frontend)
- Strict TypeScript — `"strict": true` in tsconfig
- No `any` types
- Server components for data fetching where possible, client components for interactivity
- TanStack Query for all server state — no raw `useEffect` + `fetch`
- shadcn/ui components only — no custom CSS unless Tailwind utilities are insufficient
- All API types shared via `lib/types.ts` — kept in sync with FastAPI response schemas

### Kubernetes manifests
- All manifests in `k8s/` directory, managed by Argo CD
- Always set `resources.requests` and `resources.limits`
- Always set `nodeSelector` — no pod lands on cp-01
- Never use `latest` image tag in production — use digest or semver tag
- Secrets never in manifests — use `kubectl create secret` or Sealed Secrets

### Git
- Branch: `main` (protected) → PR required
- Branch naming: `feat/v0.2-tool-registry`, `fix/agent-timeout`
- Commit style: `feat(tools): add ToolSpec versioning` (conventional commits)
- Never commit: `.env`, `*.pyc`, `__pycache__`, `node_modules`, kubeconfig files

---

## 17. What the AI Should Know When Writing Code

1. **The agent is graph-based, not a loop.** Never write a `while True` agent loop. Every step is a LangGraph node function that reads `AgentState` and returns a partial state update.

2. **Safety is non-negotiable.** Every tool call passes through `risk_classifier.py`. HIGH_RISK and CRITICAL tools must always trigger `interrupt_before` — never execute directly.

3. **Context compression is mandatory.** Never pass the full message history to the model. Always go through `ContextBudgetManager.build_context()`.

4. **Tool results are compressed before entering context.** Large vCenter responses are stored in Redis, and only a summary enters the model context.

5. **All database operations are async.** Use `async with session_factory() as session:` — never sync SQLAlchemy in an async FastAPI route.

6. **Streaming is SSE, not WebSocket, for agent tokens.** FastAPI `StreamingResponse` with `graph.astream()`. WebSocket is only for inventory push events.

7. **nodeSelector is required on every pod.** cp-01 has a NoExecute taint and must never run app workloads.

8. **The entity cache prevents repeated VM listing.** Before calling `list_vms`, always check `state["known_entities"]["vms"]` first.

9. **Every mutation is audit-logged.** After every operation_agent tool call, `audit.py` must write a row to `audit_log` with before/after state.

10. **Argo CD deploys everything.** Never suggest `kubectl apply` for production changes. All changes go through a Git push to the Helm chart repo.

---

## 18. Current Rebuild Boundaries

These boundaries apply before any coding work:

1. Do not rename `apps/frontend`, `apps/backend`, `apps/engine`, or `apps/mcp`.
2. Do not replace FastAPI, Next.js, LangGraph, LangChain, Postgres, Redis, Kubernetes, or Argo CD.
3. Do not implement real destructive vCenter or Kubernetes actions.
4. Do not expose raw `govc_command` or free-form shell execution.
5. Do not store secrets, API keys, kubeconfigs, or vCenter credentials in Git.
6. Do not store actual vCenter passwords or LLM API keys in Postgres.
7. Postgres stores only `secret_name` or `secret_ref` plus non-sensitive metadata.
8. Kubernetes Secrets store actual sensitive values.
9. Never return or log secret values.
10. Do not remove existing working endpoints unless replacing them with compatible versions.
11. Only `read_only` tools execute automatically in the current phase.
12. `low_risk`, `approval_required`, and `destructive` tools must return `TOOL_POLICY_BLOCKED` or `TOOL_REQUIRES_APPROVAL` until approval workflow exists.
