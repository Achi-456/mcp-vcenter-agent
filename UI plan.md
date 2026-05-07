Yes Achintha — **Phase 1 should focus only on building the real Next.js dashboard UI and wiring it safely to your existing FastAPI backend.**
Since your Kubernetes + CI/CD is already working, this phase should produce a usable admin console.

Main goal:

```text
Phase 1 Goal:
Build the real web dashboard where the user can configure vCenter/API credentials,
chat with the agent through SSE, view inventory data, manage sessions, and control settings.
```

Important: credentials can be entered from the dashboard, but they should **not be stored directly in browser localStorage or plain database fields**. The dashboard should send them to FastAPI, then FastAPI should store them securely as **Kubernetes Secrets / encrypted DB values / Vault later**.

---

# Phase 1 Full Plan — Real Next.js UI

## 1. Final Phase 1 Pages

Your dashboard should have these pages:

```text
/
├── /chat
├── /inventory
│   ├── /inventory/vms
│   ├── /inventory/hosts
│   ├── /inventory/datastores
│   └── /inventory/networks
├── /sessions
├── /settings
│   ├── /settings/connections
│   ├── /settings/credentials
│   ├── /settings/agent
│   └── /settings/system
└── /approvals   later phase, can show placeholder now
```

For Phase 1, build these core pages first:

```text
/chat
/inventory
/sessions
/settings
```

---

# 2. Dashboard Layout

Create a clean dashboard shell.

## Main layout components

```text
components/
├── layout/
│   ├── app-sidebar.tsx
│   ├── app-navbar.tsx
│   ├── app-shell.tsx
│   └── page-header.tsx
```

## Sidebar menu

```text
Chat
Inventory
Sessions
Settings
Approvals
System Health
```

For now, `Approvals` and `System Health` can be placeholder pages.

## Navbar should show

```text
Project name: Agentic Infrastructure Console
Current environment: dclab.local
Connection status: API online/offline
User menu
Theme toggle
```

---

# 3. Install UI Stack

Inside your Next.js app:

```bash
cd apps/web
```

Install shadcn/ui:

```bash
npx shadcn@latest init
```

Recommended options:

```text
Style: New York
Base color: Zinc or Slate
CSS variables: Yes
Tailwind config: tailwind.config.ts
Global CSS: app/globals.css
Components alias: @/components
Utils alias: @/lib/utils
```

Install useful shadcn components:

```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
npx shadcn@latest add textarea
npx shadcn@latest add label
npx shadcn@latest add form
npx shadcn@latest add select
npx shadcn@latest add table
npx shadcn@latest add tabs
npx shadcn@latest add dialog
npx shadcn@latest add alert
npx shadcn@latest add badge
npx shadcn@latest add separator
npx shadcn@latest add dropdown-menu
npx shadcn@latest add sonner
npx shadcn@latest add switch
```

Install form and validation tools:

```bash
npm install react-hook-form zod @hookform/resolvers
```

Install table helper:

```bash
npm install @tanstack/react-table
```

Install icons:

```bash
npm install lucide-react
```

Optional but useful:

```bash
npm install date-fns
```

---

# 4. Recommended Frontend Folder Structure

Use this structure:

```text
apps/web/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── chat/
│   │   └── page.tsx
│   ├── inventory/
│   │   └── page.tsx
│   ├── sessions/
│   │   └── page.tsx
│   └── settings/
│       └── page.tsx
├── components/
│   ├── layout/
│   ├── chat/
│   ├── inventory/
│   ├── sessions/
│   ├── settings/
│   └── ui/
├── lib/
│   ├── api.ts
│   ├── sse.ts
│   ├── types.ts
│   └── validators.ts
└── hooks/
    ├── use-api-health.ts
    ├── use-sse-chat.ts
    └── use-inventory.ts
```

---

# 5. Backend API Contract Needed for Phase 1

Your existing FastAPI should expose these endpoints.

## Health

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",
  "service": "api",
  "version": "0.1.0"
}
```

---

## Chat SSE endpoint

```http
POST /api/v1/chat/stream
```

Request:

```json
{
  "session_id": "optional-session-id",
  "message": "List all VMs",
  "context": {
    "environment": "dclab.local"
  }
}
```

SSE events:

```text
event: start
data: {"session_id":"abc123"}

event: token
data: {"content":"Checking vCenter inventory..."}

event: tool_call
data: {"tool":"list_vms","status":"running"}

event: tool_result
data: {"tool":"list_vms","status":"success"}

event: final
data: {"content":"I found 12 VMs."}

event: done
data: {}
```

Frontend should consume this stream and update the chat UI live.

---

## Inventory

```http
GET /api/v1/inventory/vms
GET /api/v1/inventory/hosts
GET /api/v1/inventory/datastores
GET /api/v1/inventory/networks
```

Example VM response:

```json
{
  "items": [
    {
      "name": "agentic-worker-01",
      "power_state": "poweredOn",
      "cpu": 4,
      "memory_gb": 12,
      "host": "esxi-01.dclab.local",
      "datastore": "datastore01",
      "ip_address": "192.168.1.50"
    }
  ]
}
```

---

## Sessions

```http
GET /api/v1/sessions
GET /api/v1/sessions/{session_id}
DELETE /api/v1/sessions/{session_id}
```

Session list response:

```json
{
  "items": [
    {
      "id": "session-001",
      "title": "List all VMs",
      "created_at": "2026-05-04T10:20:00Z",
      "updated_at": "2026-05-04T10:25:00Z",
      "message_count": 6
    }
  ]
}
```

---

## Settings

```http
GET /api/v1/settings
PUT /api/v1/settings
```

Used for general app settings.

---

## Credentials

This is the important part.

Do **not** expose saved passwords back to the frontend.

Use these endpoints:

```http
POST /api/v1/connections/vcenter
GET /api/v1/connections/vcenter/status
POST /api/v1/connections/vcenter/test
DELETE /api/v1/connections/vcenter
```

Dashboard form sends:

```json
{
  "name": "dclab-vcenter",
  "vcenter_url": "https://vcenter.dclab.local",
  "username": "administrator@vsphere.local",
  "password": "secret",
  "verify_ssl": false
}
```

Backend stores it securely.

Status response should only return safe metadata:

```json
{
  "configured": true,
  "name": "dclab-vcenter",
  "vcenter_url": "https://vcenter.dclab.local",
  "username_hint": "administrator@vsphere.local",
  "last_test_status": "success",
  "last_tested_at": "2026-05-04T10:30:00Z"
}
```

Never return:

```text
password
access token
refresh token
secret key
private key
```

---

# 6. Credentials Dashboard Design

Create this page:

```text
/settings/credentials
```

Or keep it inside:

```text
/settings
```

## Credential sections

```text
1. vCenter Connection
2. FastAPI internal settings
3. Tool registry settings
4. LLM provider settings
5. Redis/Postgres status only
```

For Phase 1, only implement:

```text
vCenter Connection
LLM Provider Connection
```

---

## vCenter form fields

```text
Connection name
vCenter URL
Username
Password
Verify SSL switch
Test connection button
Save credentials button
Delete credentials button
```

Example UI behavior:

```text
User enters credentials
        ↓
Clicks "Test Connection"
        ↓
Frontend calls POST /api/v1/connections/vcenter/test
        ↓
FastAPI tries login to vCenter
        ↓
Returns success/fail
        ↓
User clicks Save
        ↓
FastAPI stores secret
```

---

## LLM provider form fields

If you use OpenAI/OpenRouter/local model later:

```text
Provider: OpenAI / OpenRouter / Local
Base URL
Model name
API key
Temperature
Max tokens
Test model button
Save button
```

Again, never return API key to frontend.

Status response:

```json
{
  "configured": true,
  "provider": "openrouter",
  "model": "anthropic/claude-sonnet-4.5",
  "api_key_set": true
}
```

---

# 7. Secure Credential Storage Plan

For your current RKE2 cluster, I recommend this order.

## Phase 1 simple secure option

Store credentials as Kubernetes Secrets.

Example:

```text
Secret name: agentic-vcenter-credentials
Namespace: agentic
Keys:
  VCENTER_URL
  VCENTER_USERNAME
  VCENTER_PASSWORD
  VCENTER_VERIFY_SSL
```

FastAPI should create/update this secret using Kubernetes API.

Backend deployment needs RBAC permission only for this secret.

```text
FastAPI service account
        ↓
Can get/create/update/delete only specific secrets
        ↓
agentic-vcenter-credentials
```

Do not allow wildcard secret access if possible.

---

## Later production option

For v1.0, move to:

```text
HashiCorp Vault
External Secrets Operator
Sealed Secrets
SOPS + Age
```

But for Phase 1, Kubernetes Secret is okay for your lab.

---

# 8. Frontend Environment Variables

In Next.js, keep only public backend URL:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.dclab.local
```

Do **not** store secrets in:

```text
.env.local
NEXT_PUBLIC_*
browser localStorage
cookies without encryption
frontend source code
GitHub repo
```

---

# 9. Chat Page Plan

Path:

```text
/chat
```

Components:

```text
components/chat/
├── chat-window.tsx
├── chat-message.tsx
├── chat-input.tsx
├── tool-event-card.tsx
└── session-selector.tsx
```

UI sections:

```text
Left: session list
Center: chat window
Bottom: prompt input
Right optional: tool trace panel
```

For Phase 1, keep it simple:

```text
Chat messages
Streaming assistant response
Tool event badges
New chat button
Stop generation button
```

Example visible stream:

```text
User:
List all VMs

Assistant:
Checking vCenter connection...

Tool: list_vms running
Tool: list_vms success

I found 8 virtual machines...
```

---

# 10. Inventory Page Plan

Path:

```text
/inventory
```

Use tabs:

```text
VMs
Hosts
Datastores
Networks
```

Use TanStack Table.

VM columns:

```text
Name
Power State
CPU
Memory
Host
Datastore
IP Address
Tools / Actions
```

Host columns:

```text
Name
Connection State
CPU Total
Memory Total
VM Count
Cluster
```

Datastore columns:

```text
Name
Capacity
Free Space
Used %
Type
Accessible
```

Actions in Phase 1 should be read-only:

```text
Refresh
View details
Copy name
```

Do not add:

```text
Power off
Delete VM
Migrate VM
Snapshot delete
```

Those need approval flow later.

---

# 11. Sessions Page Plan

Path:

```text
/sessions
```

Purpose:

```text
Show previous agent conversations and execution history.
```

Columns:

```text
Title
Session ID
Created time
Last updated
Message count
Status
Actions
```

Actions:

```text
Open
Rename
Delete
```

Session detail can show:

```text
Messages
Tool calls
Final answer
Errors
```

---

# 12. Settings Page Plan

Path:

```text
/settings
```

Use tabs:

```text
Connections
Credentials
Agent
System
```

## Connections tab

```text
FastAPI status
Agent Engine status
MCP server status
Redis status
Postgres status
vCenter status
```

## Credentials tab

```text
vCenter credentials form
LLM provider API key form
```

## Agent tab

```text
Default model
Max tool calls
Enable tool tracing
Require approval for risky tools
Default session timeout
```

## System tab

```text
API base URL
Environment name
Git commit version
Build version
Kubernetes namespace
```

---

# 13. Phase 1 Implementation Order

Do the work in this exact order.

## Step 1 — UI foundation

```text
Install shadcn/ui
Install Tailwind support
Add app shell
Add sidebar
Add navbar
Add routing
Add theme
```

Result:

```text
Dashboard opens successfully.
Navigation works.
No backend connection needed yet.
```

---

## Step 2 — API client

Create:

```text
lib/api.ts
```

Responsibilities:

```text
Base URL from NEXT_PUBLIC_API_BASE_URL
GET helper
POST helper
PUT helper
DELETE helper
Error handling
```

Example functions:

```text
getHealth()
getInventoryVMs()
getSessions()
getSettings()
saveVCenterCredentials()
testVCenterConnection()
```

---

## Step 3 — Health connection

Create API status indicator in navbar.

```text
Green = API online
Red = API offline
Yellow = degraded
```

Call:

```http
GET /api/v1/health
```

---

## Step 4 — Settings credentials form

Build this before chat because chat needs valid vCenter settings.

Flow:

```text
User opens Settings
        ↓
Enters vCenter credentials
        ↓
Clicks Test Connection
        ↓
If success, Save
        ↓
Backend stores Kubernetes Secret
```

---

## Step 5 — Inventory page

After credentials work, build inventory.

Flow:

```text
Inventory page loads
        ↓
GET /api/v1/inventory/vms
        ↓
Display table
        ↓
Refresh button reloads data
```

---

## Step 6 — Chat page with SSE

Build SSE consumer.

Flow:

```text
User sends message
        ↓
POST stream request
        ↓
Read SSE chunks
        ↓
Update assistant message live
        ↓
Display tool calls
```

---

## Step 7 — Sessions page

Build history after chat works.

Flow:

```text
GET /api/v1/sessions
        ↓
Show session table
        ↓
Click session
        ↓
Open chat with session_id
```

---

## Step 8 — Polish

```text
Loading states
Error states
Empty states
Toast notifications
Responsive layout
Form validation
Confirm delete dialogs
```

---

# 14. Backend Changes Needed for Credentials

FastAPI needs these modules:

```text
apps/api/app/
├── routers/
│   ├── health.py
│   ├── inventory.py
│   ├── chat.py
│   ├── sessions.py
│   └── connections.py
├── services/
│   ├── k8s_secret_store.py
│   ├── vcenter_client.py
│   └── settings_service.py
└── schemas/
    ├── connections.py
    ├── inventory.py
    └── chat.py
```

Important backend behavior:

```text
Dashboard sends credentials
FastAPI validates input
FastAPI tests connection
FastAPI writes Kubernetes Secret
FastAPI restarts/reloads agent-engine config if needed
Agent Engine reads credentials from env/secret
```

For Phase 1, simplest reload method:

```text
Save secret
        ↓
Tell user "restart required"
        ↓
kubectl rollout restart deployment/agent-engine
```

Better later:

```text
Agent Engine reloads credentials dynamically.
```

---

# 15. Kubernetes Secret Design

Create one secret per connection.

```text
agentic-vcenter-default
agentic-llm-provider-default
```

Example values:

```text
VCENTER_URL
VCENTER_USERNAME
VCENTER_PASSWORD
VCENTER_VERIFY_SSL
```

LLM secret:

```text
LLM_PROVIDER
LLM_BASE_URL
LLM_MODEL
LLM_API_KEY
```

FastAPI needs RBAC:

```text
get secrets
create secrets
update secrets
patch secrets
delete secrets
```

But restrict namespace to your app namespace.

---

# 16. Phase 1 Definition of Done

Phase 1 is complete when these are working:

```text
1. Dashboard has real layout with sidebar and navbar.
2. Settings page can enter vCenter credentials.
3. Test connection button verifies vCenter access.
4. Save button stores credentials securely through FastAPI.
5. Inventory page can show VM/host/datastore data.
6. Chat page can send prompt to FastAPI.
7. Chat page can receive SSE streaming response.
8. Sessions page shows previous chat sessions.
9. No credentials are exposed back to frontend.
10. CI/CD builds and deploys the Next.js app automatically.
```

---

# 17. Recommended Phase 1 Milestones

## Phase 1.1 — Dashboard shell

```text
Navbar
Sidebar
Routing
Theme
Basic pages
```

## Phase 1.2 — Settings and credentials

```text
vCenter form
LLM form
Test connection
Save secret
Connection status
```

## Phase 1.3 — Inventory tables

```text
VM table
Host table
Datastore table
Refresh button
Empty/error states
```

## Phase 1.4 — Chat SSE

```text
Chat input
Streaming assistant message
Tool call events
Session ID handling
```

## Phase 1.5 — Sessions

```text
Session history
Open previous session
Delete session
```

---

# 18. Best Cursor/Codex Prompt for Phase 1

Use this as your coding-agent prompt:

```text
You are working inside my existing agentic infrastructure project.

Current state:
- RKE2 Kubernetes cluster is working.
- CI/CD and Argo CD GitOps are working.
- Existing services include Next.js frontend, FastAPI backend, MCP server, and agent-engine.
- Do not change the main architecture.
- Do not replace FastAPI, LangGraph, Redis, Postgres, or Kubernetes manifests unless required.
- Focus only on Phase 1: real Next.js dashboard UI.

Build Phase 1 dashboard:
1. Install and configure shadcn/ui with Tailwind.
2. Create a dashboard layout shell with sidebar and navbar.
3. Create pages:
   - /chat
   - /inventory
   - /sessions
   - /settings
4. Create Settings page with credential forms:
   - vCenter URL
   - Username
   - Password
   - Verify SSL
   - Test Connection button
   - Save Credentials button
5. Credentials must never be saved in localStorage or frontend code.
6. Credentials must be sent to FastAPI endpoints only.
7. Frontend must never display saved passwords.
8. Create API client in lib/api.ts using NEXT_PUBLIC_API_BASE_URL.
9. Create SSE consumer for chat streaming.
10. Create inventory table using TanStack Table.
11. Use shadcn/ui components for all forms, tables, cards, alerts, and buttons.
12. Add clean loading, error, and empty states.
13. Keep all dangerous actions hidden for Phase 1.
14. Do not implement VM power operations, delete operations, or migration yet.
15. Make the UI production-clean and easy to extend for later approval workflow.

Expected result:
A working Next.js dashboard connected to existing FastAPI with pages for chat, inventory, sessions, and settings.
```

---

My recommendation: start with **Phase 1.1 + Phase 1.2 first**.
Because once credentials can be entered and tested from the dashboard, your inventory and chat features become much easier to build.
