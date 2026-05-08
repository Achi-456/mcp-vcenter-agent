# Phase 1.3 — Real vCenter Inventory + Chat-Ready Context

> **Branch**: `main-rke2-mcp` | **Commit**: `d713dc4` | **Date**: 2026-05-08

---

## What Phase 1.3 Delivers

```
User opens https://infra-agent-console.dclab.local/
  → Dashboard shows real vCenter summary cards
  → VM inventory table with live power states
  → Datastore usage panels with progress bars
  → Active alarms panel with severity badges
  → Recent events timeline
  → AI Assistant slide-out panel (right side)
     → Provider selector: Gemini / Claude / OpenAI / Grok / Kimi
     → Model selector (changes per provider)
     → 6 prompt shortcuts for quick context queries
     → Tool trace panel
     → High-risk action safety gate
  → Monitoring page: alarms + events tables
  → Inventory page: 5 tabs (VMs, Hosts, Clusters, Datastores, Networks)

All data sourced from real vCenter via pyVmomi, credentials from K8s Secret.
```

---

## Architecture — Data Flow

```
Frontend (Next.js)                     Backend (FastAPI)                vCenter
─────────────────                      ─────────────────                ───────
lib/api.ts ──GET──►  /api/v1/inventory/*  ──►  vcenter_client_factory.py
                    /api/v1/monitoring/*            │
                    /api/v1/context/*               ▼
                    /api/v1/llm/*            with_vcenter(fn)
                                               │
                                          get_vcenter_credentials()
                                               │
                                          K8s Secret: agentic-vcenter-default
                                               │
                                          SmartConnect() ──► vCenter SOAP API
                                               │
                                          ContainerView → VMs/Hosts/DS/Nets
                                               │
                                          ThreadPoolExecutor (async-safe)
                                               │
                                          Redis Cache ←── results cached
                                               │
                                          Safe JSON ←─ passwords stripped
```

---

## Backend — New Files

```
apps/backend/
├── app/api/
│   ├── main.py                              # +3 router registrations
│   ├── routes/
│   │   ├── inventory.py                     # (modified) added clusters
│   │   ├── monitoring.py                    # NEW — alarms + events
│   │   ├── context.py                       # NEW — 6 context helpers
│   │   └── llm.py                           # NEW — providers/models/status
│   └── schemas/
│       └── inventory.py                     # (modified) +AlarmItem, EventItem, ContextResponse, LLMProvider, LLMModel, LLMStatus
├── app/services/
│   ├── vcenter_inventory_service.py         # (modified) +alarms, +events, +6 context helpers
│   └── vcenter_client_factory.py            # (modified) +async_with_vcenter, ThreadPoolExecutor
└── app/core/
    └── inventory_errors.py                  # unchanged (reused error codes)
```

## Backend — API Endpoints

### Inventory (`/api/v1/inventory`)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/overview` | Summary: VMs, Hosts, Datastores, Networks, Alarms |
| GET | `/vms` | VM list with `?refresh=true` bypass |
| GET | `/hosts` | ESXi host list |
| GET | `/clusters` | Cluster list |
| GET | `/datastores` | Datastore capacity/free/used |
| GET | `/networks` | Network/portgroup list |

### Monitoring (`/api/v1/monitoring`) — NEW

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/alarms` | Active vCenter alarms via `AlarmManager` |
| GET | `/events` | Recent events via `EventManager` (`?limit=50`) |

### Context (`/api/v1/context`) — NEW

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/environment` | Environment overview summary |
| GET | `/powered-off-vms` | VMs not powered on |
| GET | `/datastore-health` | Healthy/warning/critical breakdown |
| GET | `/active-alarms` | Alarm summary sorted by severity |
| GET | `/recent-events` | Event summary with error/warn counts |
| GET | `/rke2-vms` | VMs matching "agentic/rke2/cp-/worker-/db-/utility-" |

### LLM (`/api/v1/llm`) — NEW

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/providers` | Available LLM providers + models |
| GET | `/models?provider=` | Models for selected provider |
| GET | `/llm/status` | Current LLM configuration state |

---

## Backend — vCenter Integration

### Connection Pattern

```python
# Factory (short-lived connections)
with_vcenter(fn)  # sync — blocks event loop
async_with_vcenter(fn)  # async — ThreadPoolExecutor(max_workers=3)
```

### pyVmomi Container Views Used

```
vim.VirtualMachine       → list_vms()
vim.HostSystem           → list_hosts()
vim.Datastore            → list_datastores()
vim.Network              → list_networks()
vim.ClusterComputeResource → list_clusters()
AlarmManager.GetAlarm()  → list_alarms()       (NEW)
EventManager.CreateCollectorForEvents() → list_events()  (NEW)
```

### Cache TTLs

| Endpoint | TTL |
|---|---|
| Overview | 15s |
| VMs, Hosts | 30s |
| Datastores, Networks, Clusters | 60s |
| Alarms | 60s |
| Events | 30s |
| Context helpers | 15–60s |

Cache keys: `inventory:overview`, `monitoring:alarms`, `context:environment`, etc.

### Safety Rules Enforced

```
No passwords in responses
No passwords in logs
Read-only operations only
Friendly error codes (not stack traces)
Self-signed cert support via VCENTER_VERIFY_SSL=false
```

---

## Backend — LLM Providers

Hardcoded provider registry in `llm.py`:

| ID | Name | Models |
|---|---|---|
| `gemini` | Google Gemini | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| `claude` | Anthropic Claude | claude-sonnet-4-20250514, claude-3-opus, claude-3-haiku |
| `openai` | OpenAI | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| `grok` | xAI Grok | grok-3, grok-3-mini |
| `kimi` | Kimi / Moonshot | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k |

---

## Frontend — New Files

```
apps/frontend/
├── app/
│   ├── page.tsx                         # (rewritten) Dashboard with summary cards + 4 panels + quick links
│   ├── inventory/
│   │   └── page.tsx                     # (rewritten) 5 tabs + AI assistant toggle + overview cards
│   ├── monitoring/
│   │   └── page.tsx                     # NEW — alarms + events tables with tabs, overview cards
│   └── inventory/                       # (unchanged)
├── components/
│   ├── chat/
│   │   └── ai-assistant-panel.tsx       # NEW — full AI Assistant slide-out panel
│   └── layout/
│       └── app-sidebar.tsx              # (modified) +Dashboard, +Monitoring nav items
├── lib/
│   └── api.ts                           # (rewritten) 30+ typed API endpoints
└── hooks/
    └── use-sse-chat.ts                  # (unchanged)
```

---

## Frontend — Page Details

### Dashboard (`/`)

```
┌───────────────────────────────────────────────────────┬──────────────┐
│ Dashboard Header                 [time] [cached]     │              │
├───────────────────────────────────────────────────────┤   AI         │
│ [Total VMs] [Powered On] [Hosts] [Alarms] [DS Used%] │   Assistant  │
├─────────────────────────┬─────────────────────────────┤   Panel      │
│ VM Table (top 5)        │ Datastore Usage Bars        │   (380px)    │
│ Name | Power | CPU | Mem│ DS1 ████████░░ 45%         │              │
│ agentic-cp-01  | on    │ DS2 ████████████ 72%        │   Provider:  │
│ agentic-worker-01| on   │ DS3 ██████░░░░░░ 31%       │   [Gemini v] │
├─────────────────────────┼─────────────────────────────┤   Model:     │
│ Active Alarms           │ Recent Events               │   [flash  v] │
│ ⚠ Host CPU warning      │ ● VM powered on             │              │
│ ⚠ Datastore usage       │ ● Alarm acknowledged        │   Shortcuts: │
├─────────────────────────┴─────────────────────────────┤   [Env] [Off]│
│ Quick Links: [AI Chat] [Inventory] [Monitor] [Setting]│   [DS] [Alm] │
└───────────────────────────────────────────────────────┴──────────────┘
```

### Inventory (`/inventory`)

5 tabs: **VMs | Hosts | Clusters | Datastores | Networks**

- VMs: Name, Power (badge), CPU, Memory, OS, IP, Host, Tools
- Hosts: Name, Connection, CPU cores×threads, Memory, VM Count, Version
- Clusters: Name, Hosts, VMs, CPU MHz, Memory (NEW)
- Datastores: Name, Type, Capacity, Free, Used% (progress bar), Accessible
- Networks: Name, Type, Accessible
- Overview cards above tabs: Total VMs, Hosts, Datastores, Networks, Capacity
- AI Assistant toggle button in header
- VCENTER_NOT_CONFIGURED → Settings button card

### Monitoring (`/monitoring`) — NEW

2 tabs: **Alarms | Events**

- Overview cards: Total Alarms, Warnings, Error Events, Warning Events
- Alarms table: Severity (badge), Name, Entity, Type, Acknowledged
- Events table: Level (dot), Message, Entity, User, Timestamp
- VCENTER_NOT_CONFIGURED → Settings button card

### AI Assistant Panel

Slide-out panel (380px, fixed right):

```
┌──────────────────────────────┐
│ 🤖 AI Assistant    ● Connected│
├──────────────────────────────┤
│ Provider: [Gemini v]          │
│ Model:    [flash v]           │
├──────────────────────────────┤
│ QUICK ACTIONS                 │
│ [🌐 Environment] [⚡ Off VMs] │
│ [💾 DS Health]   [🔔 Alarms] │
│ [🕐 Events]      [🖥 RKE2 VMs]│
├──────────────────────────────┤
│ Messages area                 │
│ ┌─ User: Run: Environment ──┐│
│ └────────────────────────────┘│
│ ┌─ Assistant: Summary... ───┐│
│ └────────────────────────────┘│
├──────────────────────────────┤
│ TOOL TRACE                    │
│ ✓ context/environment done    │
├──────────────────────────────┤
│ ☐ High-Risk Actions           │
│ [Ask about your vCenter...] >│
└──────────────────────────────┘
```

**Safety Gate**: If user types "power off" or "delete" without the High-Risk checkbox, the assistant blocks the request and explains why.

---

## Frontend — API Client

`lib/api.ts` now has 30+ typed endpoints:

```typescript
// Inventory
api.getInventoryOverview()  api.getVMs()  api.getHosts()  api.getDatastores()
api.getNetworks()           api.getClusters()

// Monitoring (NEW)
api.getAlarms()             api.getEvents()

// Context (NEW)
api.getContextEnvironment()       api.getContextPoweredOff()
api.getContextDatastoreHealth()   api.getContextActiveAlarms()
api.getContextRecentEvents()      api.getContextRKE2VMs()

// LLM (NEW)
api.getLLMProviders()       api.getLLMModels(provider)    api.getLLMStatus()

// Connections (Phase 1.2)
api.testVCenterConnection() api.saveVCenterConnection()
api.getVCenterConnectionStatus()  api.deleteVCenterConnection()
api.testLLMConnection()     api.saveLLMConnection()
api.getLLMConnectionStatus()      api.deleteLLMConnection()

// Sessions, Settings, Tools
api.getSessions()  api.getSession(id)  api.getSettings()
api.updateSetting()  api.testVcenter()  api.testLLM()
api.getSettingsStatus()  api.getTools()  api.health()
```

---

## Design System Updates

```
Theme:      Dark Slate (#09090B) — unchanged
Primary:    Emerald (#10B981) — unchanged
New Icons:  LayoutDashboard, BarChart3, Bell, Clock, AlertTriangle,
            XCircle, CheckCircle2, Shield, Wrench, Zap, Grid3X3,
            Info, Bot, ChevronRight
Layout:     +380px right panel when AI Assistant is open
            Dashboard/inventory/monitoring pages shift left via mr-[380px]
```

---

## Build Output

```
Route (app)                                 Size    First Load JS
/                                        3.21 kB         154 kB
/_not-found                                996 B         103 kB
/api/health                                123 B         103 kB
/chat                                     4.1 kB         115 kB
/health                                  3.31 kB         114 kB
/inventory                               3.05 kB         154 kB
/monitoring                               6.00 kB         157 kB    ← NEW
/sessions                                4.58 kB         115 kB
/settings                                8.46 kB         140 kB
```

---

## Deployment Verification

### Argo CD

| Application | Sync | Health | Revision |
|---|---|---|---|
| agentic-app | Synced | Healthy | `d713dc4` |
| agentic-agents | Synced | Healthy | `b9510f3` (unchanged) |

### Kubernetes Pods

| Deployment | Ready | Image SHA | Matches Commit |
|---|---|---|---|
| fastapi | 1/1 | `d713dc4` | Yes |
| nextjs | 1/1 | `d713dc4` | Yes |
| mcp-server | 1/1 | `476da9d` | N/A |
| agent-engine | 1/1 | `5a32f70` | N/A |

### Endpoint Verification

```
/api/v1/llm/providers        → 200 (5 providers: Gemini, Claude, OpenAI, Grok, Kimi)
/api/v1/llm/models           → 200
/api/v1/llm/status           → 200
/api/v1/monitoring/alarms    → 200 (363 real vCenter alarms returned)
/api/v1/monitoring/events    → 200
/api/v1/inventory/overview   → 200
/api/v1/inventory/clusters   → 200
/api/v1/inventory/vms        → 200
/api/v1/inventory/hosts      → 200
/api/v1/inventory/datastores → 200
/api/v1/inventory/networks   → 200
/api/v1/context/environment  → 200 (cached)
```

---

## Security Checklist

| Rule | Status |
|---|---|
| Passwords never returned in API responses | Passed |
| Passwords never logged | Passed |
| All vCenter operations read-only | Passed |
| Self-signed cert support (VCENTER_VERIFY_SSL=false) | Passed |
| Friendly error codes (not stack traces) | Passed |
| High-risk actions blocked in AI Assistant | Passed |
| High-risk checkbox default unchecked | Passed |
| Cache `?refresh=true` bypass works | Passed |
| No `latest` image tag used | Passed |
| NodeSelector on all pods | Passed |

---

## Known Limitations

| Item | Detail |
|---|---|
| Alarm severity detection | All alarms show as "unknown" — `GetAlarm()` returns definition objects, not triggered instances |
| Slow first context call | Uncached `/context/environment` aggregates 5 vCenter queries; 15s timeout |
| Chat endpoint mismatch | Frontend calls `/api/v1/chat`, backend exposes `/api/v1/agent/run` (Phase 1.4 fix) |
| AI Assistant not connected to agent | Prompt shortcuts call context endpoints directly; no LLM inference yet |
| No Postgres/Redis in cluster | Required for LangGraph checkpointer and persistent entity cache |
| vCenter calls still sync | `async_with_vcenter` exists but inventory routes still use sync `with_vcenter` |

---

## Next Phase

- **Phase 1.4**: Chat SSE connected to real agent tools
  - Bridge local agent engine (`app/agent/engine.py`) to LangGraph cluster engine (`apps/engine/`)
  - Wire vCenter tools into agent as `ToolSpec` registrations
  - Fix chat endpoint (`/api/v1/chat` → `/api/v1/agent/run`)
  - Enable LLM inference in AI Assistant panel
  - Deploy Postgres + Redis to cluster
