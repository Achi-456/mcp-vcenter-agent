# Solution Build — vCenter Agentic Ops Platform

> **Branch**: `main-rke2-mcp` | **Commit**: `297d6a4` | **Date**: 2026-05-07

---

## Phase 1.1 — shadcn/ui Dashboard Shell

### Design System

```
Theme:      Dark Slate (#09090B)
Primary:    Emerald (#10B981)
Agent:      Cyan (#22D3EE)
Success:    #22C55E
Warning:    Amber (#F59E0B)
Error:      Red (#EF4444)
Font:       Inter (body), JetBrains Mono (code/hostnames)
Icons:     lucide-react
```

### Layout

```
┌───────────────────────────────────────────────┐
│ Navbar 64px: Infrastructure Console | API ●   │
├──────────────┬────────────────────────────────┤
│ Sidebar 260px│ Page Content                   │
│              │                                │
│ ● Chat       │ Cards / Tables / Forms         │
│ ● Inventory  │                                │
│ ● Sessions   │                                │
│ ● Settings   │                                │
│ ● Health     │                                │
└──────────────┴────────────────────────────────┘
```

### Technology Stack

```text
Framework:   Next.js 15.5 + React 19 + TypeScript 5.7 (strict)
UI:          shadcn/ui New York + Tailwind CSS 3.4
Table:       @tanstack/react-table
Forms:       react-hook-form + zod + @hookform/resolvers
Icons:       lucide-react
Dates:       date-fns
Utilities:   clsx + tailwind-merge (cn() helper)
Toasts:      sonner (shadcn sonner)
```

### Shadcn/ui Components Installed

```text
button  card  input  textarea  label  form  select
table  tabs  dialog  alert  badge  separator
dropdown-menu  sonner  switch
```

---

## File Structure

```
apps/frontend/
├── components.json                          # shadcn/ui config (New York, Slate)
├── tailwind.config.ts                       # Dark theme with CSS variables
├── tsconfig.json                            # Added @/* path alias
├── package.json                             # Added 11 deps
│
├── app/
│   ├── globals.css                          # Dark theme CSS variables
│   ├── layout.tsx                           # Root layout with AppShell + Toaster
│   ├── page.tsx                             # Dashboard home — 5 card grid
│   ├── chat/
│   │   └── page.tsx                         # Chat with SSE streaming + plan cards
│   ├── inventory/
│   │   └── page.tsx                         # VMs/Hosts/Datastores table with tabs
│   ├── sessions/
│   │   └── page.tsx                         # Session history table
│   ├── settings/
│   │   └── page.tsx                         # Credentials + config with test buttons
│   └── health/
│       └── page.tsx                         # System health status cards
│
├── components/
│   ├── layout/
│   │   ├── app-sidebar.tsx                  # 260px sidebar with nav + status dots
│   │   ├── app-navbar.tsx                   # 64px top bar with API status
│   │   ├── app-shell.tsx                    # Shell wrapper
│   │   └── index.ts                         # barrel export
│   └── ui/                                  # 16 shadcn/ui components
│
├── hooks/
│   ├── use-api-health.ts                    # 30s polling health check
│   └── use-sse-chat.ts                      # SSE chat stream with abort
│
└── lib/
    ├── api.ts                               # Typed fetch client (all endpoints)
    └── utils.ts                             # cn() helper
```

---

## Page Details

### Dashboard (`/`)
- 5-card grid: Chat, Inventory, Sessions, Settings, System Health
- Each card has lucide icon + Open button

### Chat (`/chat`)
- Message bubbles (user=right/emerald, agent=left/slate)
- SSE streaming via `useSSEChat` hook
- Plan card: shows goal, risk badge, steps with tool names
- Node trace badges under agent messages
- New Session button, session ID display
- Stop generation button during streaming
- Error cards with inline display

### Inventory (`/inventory`)
- Tabs: VMs | Hosts | Datastores
- Data via `lib/api.ts` → FastAPI endpoints
- Refresh button top-right
- VM table: Name, Power State (badge), CPU, Memory, Host, IP
- Host table: Name, Connection State, CPU Cores, Memory, VM Count
- Datastore table: Name, Type, Capacity, Free, Used% (progress bar)
- Error state card
- Loading state text

### Sessions (`/sessions`)
- Session history table: Title, ID, Created, Message Count
- Refresh button
- Empty state with call-to-action

### Settings (`/settings`)
- Sidebar category nav: vCenter | LLM | Agent | User
- Each setting: card with label + input + Save button
- Password fields masked (type=password)
- Test vCenter Connection button → calls `/api/v1/settings/test/vcenter`
- Test LLM Connection button → calls `/api/v1/settings/test/llm`
- Test result card (green success / red error)
- Connection status in page header

### System Health (`/health`)
- Health status cards: FastAPI, Agent Engine, Postgres, Redis, vCenter
- Online (emerald) / Offline (red) / Checking (amber) badges
- Uses `useApiHealth` hook

---

## API Contract (Frontend → Backend)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | API health check |
| POST | `/api/v1/chat` | SSE agent chat stream |
| GET | `/api/v1/inventory/vms` | VM list |
| GET | `/api/v1/inventory/hosts` | Host list |
| GET | `/api/v1/inventory/datastores` | Datastore list |
| GET | `/api/v1/sessions` | Session list |
| GET | `/api/v1/sessions/{id}` | Session detail |
| GET | `/api/v1/settings` | All settings |
| PUT | `/api/v1/settings/{key}` | Update setting |
| POST | `/api/v1/settings/test/vcenter` | Test vCenter connection |
| POST | `/api/v1/settings/test/llm` | Test LLM connection |
| GET | `/api/v1/settings/status` | Connection status |
| GET | `/api/v1/tools` | Tool registry |

---

## Environment Variables

```env
NEXT_PUBLIC_API_BASE_URL=https://api.dclab.local
```

Set via Docker build arg in CI:
```yaml
# .github/workflows/build-frontend.yml
build-args:
  NEXT_PUBLIC_API_BASE_URL=https://api.dclab.local
```

> The frontend runs at `infra-agent-console.dclab.local`, API at `api.dclab.local`.

---

## Build Output

```
Route (app)          Size    First Load JS
/                    171 B   107 kB
/_not-found          996 B   103 kB
/api/health          123 B   103 kB
/chat                4.03 kB 115 kB
/health              3 kB    114 kB
/inventory           1.76 kB 116 kB
/sessions            871 B   115 kB
/settings            3.63 kB 114 kB
```

---

## Deployment

```text
Image:      ghcr.io/achi-456/agentic-nextjs:<commit-sha>
Registry:   GHCR (GitHub Container Registry)
CI:         .github/workflows/build-frontend.yml
GitOps:     Argo CD → k8s/apps/agentic-app/nextjs/deployment.yaml
Hostname:   infra-agent-console.dclab.local
TLS:        cert-manager self-signed for dclab.local
Ingress:    nginx (rke2-ingress-nginx-controller, RKE2 bundled)
Node:       agentic-worker-01.dclab.local (role=app-worker)
```

## Naming Convention

```
Project uses:    apps/frontend  (consistent everywhere)
Not:             apps/web       (avoid this)
```

All references use `apps/frontend`:
- `Dockerfile` context: `apps/frontend`
- `GitHub Actions` paths: `apps/frontend/**`
- `Kubernetes` manifests: `k8s/apps/agentic-app/nextjs/`
- `Argo CD` path: `k8s/apps/agentic-app`
- `AGENTS.md`: `apps/frontend/`

---

## Next Phase

- **Phase 1.2**: Settings & credentials — backend wiring to store as K8s Secrets
- **Phase 1.3**: Inventory — real vCenter data with pyVmomi
- **Phase 1.4**: Chat — real agent engine with LLM integration
- **Phase 1.5**: Sessions — persistent session store in Postgres
