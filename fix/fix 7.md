# Fix 7 — Dashboard Data Persistence, Provider Model Loading, and Chat Panel UX

## Focus Area

This fix focuses on frontend reliability and usability after the core chat/tool flow started working.

Current working state:
- vCenter inventory is loading.
- Chat assistant is working.
- Provider/model selector exists.
- Tool output is visible.
- Inventory table and assistant panel are usable.

Current problems:
1. Inventory data disappears when navigating away and back while new data is loading.
2. No proper refresh button / auto-refresh behavior.
3. System Health page shows services stuck in `Checking`.
4. Provider/model selector does not fully validate API key availability.
5. When selecting a vendor/provider without an API key, the UI should guide the user to connect it.
6. Chat panel UX has layout problems: input bar overlaps/goes below taskbar, message area scroll is awkward, chat input is not expandable.

---

## Goal

After this fix:

```text
Inventory and dashboard data should feel stable.
Old data should stay visible while background refresh happens.
Refresh button should manually reload data.
Auto-refresh should run every 2 minutes.
Provider selector should fetch models dynamically.
If selected provider is not connected, show a connect modal.
Chat panel should have a fixed header, scrollable body, and fixed expandable input footer.
```

---

# Issue 1 — Inventory data disappears on navigation

## Problem

When user opens Inventory:

```text
Inventory data loads
↓
User goes to another page
↓
User comes back
↓
Old data is gone
↓
Page shows empty/loading state again until API returns
```

This creates poor UX.

## Correct behavior

```text
Inventory data loads once
↓
Store it in frontend cache/state
↓
When user navigates away and returns
↓
Show old data immediately
↓
Refresh in background
↓
Replace old data only after new data succeeds
```

## Required behavior

```text
✅ Keep previous data visible while refreshing
✅ Never clear table before new data arrives
✅ Show “Refreshing…” badge/spinner
✅ Show “Last updated at” timestamp
✅ If refresh fails, keep old data and show non-blocking error toast/card
✅ Add manual Refresh button
✅ Auto-refresh every 2 minutes
```

---

# Issue 1 implementation plan

## Step 1 — Add inventory data cache hook/store

Create one of these:

```text
apps/frontend/hooks/use-inventory-cache.ts
```

or:

```text
apps/frontend/stores/inventory-store.ts
```

Recommended state shape:

```typescript
type InventoryCacheState<T> = {
  data: T | null;
  isInitialLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastUpdatedAt: string | null;
};
```

Important rule:

```typescript
// Do NOT do this before refresh:
setData(null);

// Do this:
setIsRefreshing(true);
try {
  const newData = await apiCall();
  setData(newData);
  setLastUpdatedAt(new Date().toISOString());
} catch (error) {
  setError(error.message);
  // Keep old data
} finally {
  setIsRefreshing(false);
}
```

---

## Step 2 — Add shared auto refresh hook

Create:

```text
apps/frontend/hooks/use-auto-refresh.ts
```

Example behavior:

```typescript
export function useAutoRefresh(
  callback: () => void,
  intervalMs = 120000,
  enabled = true
) {
  useEffect(() => {
    if (!enabled) return;

    const id = window.setInterval(() => {
      callback();
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [callback, intervalMs, enabled]);
}
```

Use:

```typescript
useAutoRefresh(refreshInventory, 120000, true);
```

---

## Step 3 — Add manual Refresh button

Add to Dashboard, Inventory, and Monitoring headers:

```text
[Refresh]  [Refreshing...]  Last updated: 11:42 AM
```

Button behavior:

```text
Click Refresh
↓
Call required APIs with refresh=true
↓
Keep old data visible
↓
Update when response arrives
```

API calls:

```text
GET /api/v1/inventory/overview?refresh=true
GET /api/v1/inventory/vms?refresh=true
GET /api/v1/inventory/hosts?refresh=true
GET /api/v1/inventory/datastores?refresh=true
GET /api/v1/inventory/networks?refresh=true
GET /api/v1/monitoring/alarms?refresh=true
GET /api/v1/monitoring/events?refresh=true
```

If backend does not support `refresh=true` for monitoring yet, add it or ignore it safely.

---

## Step 4 — Persist cache across route navigation

Use one of these options.

### Option A — React Context

Create:

```text
apps/frontend/providers/inventory-provider.tsx
```

Wrap dashboard layout:

```tsx
<InventoryProvider>
  <AppShell>{children}</AppShell>
</InventoryProvider>
```

### Option B — Zustand

Install if acceptable:

```bash
npm install zustand
```

Create:

```text
apps/frontend/stores/inventory-store.ts
```

Recommended for this project:

```text
Use Zustand or React Context.
Do not keep important dashboard data only inside page-local state.
```

---

## Step 5 — Loading state rules

Use these rules:

```text
If data === null and isInitialLoading:
    show skeleton/loading

If data !== null and isRefreshing:
    show old data + small refreshing badge

If data !== null and refresh failed:
    show old data + warning toast/card

If data === null and error:
    show full error card
```

Never show blank tables if previous data exists.

---

# Issue 2 — System Health stuck on Checking

## Problem

System Health page shows:

```text
Agent Engine: Checking
Postgres: Checking
Redis: Checking
vCenter: Checking
```

This means health checks are either:
- not wired,
- endpoint missing,
- response shape mismatch,
- requests failing silently,
- or UI state not updated.

## Required endpoints

FastAPI should expose:

```text
GET /api/v1/health/services
```

or individual endpoints:

```text
GET /api/v1/agent/health
GET /api/v1/connections/vcenter/status
GET /api/v1/storage/postgres/status
GET /api/v1/storage/redis/status
```

Recommended consolidated response:

```json
{
  "fastapi": {
    "status": "online",
    "message": "API ready"
  },
  "agent_engine": {
    "status": "online",
    "message": "Engine ready"
  },
  "postgres": {
    "status": "online",
    "message": "Connected"
  },
  "redis": {
    "status": "online",
    "message": "Connected"
  },
  "vcenter": {
    "status": "online",
    "message": "Connected to core-infra-vc01.dclab.com"
  }
}
```

Allowed statuses:

```text
online
offline
degraded
checking
not_configured
```

## Frontend fix

Update:

```text
apps/frontend/hooks/use-api-health.ts
```

or create:

```text
apps/frontend/hooks/use-service-health.ts
```

Behavior:

```text
1. Fetch service health on page load.
2. Refresh every 30 seconds.
3. If endpoint missing, show Offline/Unavailable, not infinite Checking.
4. If request fails, set status=offline.
5. vCenter should use /api/v1/connections/vcenter/status.
```

Validation:

```bash
curl -k https://api.dclab.local/api/v1/agent/health
curl -k https://api.dclab.local/api/v1/connections/vcenter/status
```

UI should not stay `Checking` longer than 5–10 seconds.

---

# Issue 3 — Provider/model selector behavior

## Problem

Provider/model selector currently shows static or semi-static models.

Required behavior:
1. User selects provider.
2. Frontend sends request to backend to fetch available models for that provider.
3. Backend checks whether API key exists.
4. If provider is connected, return live models.
5. If provider is not connected, show connect modal.
6. If provider fails, show clear error.

---

## Correct provider flow

```text
User selects provider: Anthropic Claude
↓
Frontend calls GET /api/v1/llm/models?provider=claude
↓
Backend checks secret for claude API key
↓
If key exists:
    call provider models API or return cached/known list
↓
If key missing:
    return PROVIDER_NOT_CONNECTED
↓
Frontend opens connect modal
```

---

## Required backend endpoints

```text
GET /api/v1/llm/providers
GET /api/v1/llm/models?provider=gemini
GET /api/v1/llm/status?provider=gemini
POST /api/v1/connections/llm/provider
POST /api/v1/connections/llm/provider/test
```

If current Phase 1.2 uses only one LLM secret, add multi-provider support gradually.

Recommended provider secrets:

```text
agentic-llm-gemini
agentic-llm-anthropic
agentic-llm-openai
agentic-llm-xai
agentic-llm-moonshot
```

Secret keys:

```text
PROVIDER
API_KEY
BASE_URL
DEFAULT_MODEL
CREATED_AT
UPDATED_AT
LAST_TEST_STATUS
LAST_TESTED_AT
```

---

## Model request response

### Connected provider

```json
{
  "provider": "gemini",
  "connected": true,
  "models": [
    {
      "id": "gemini-2.5-flash",
      "label": "Gemini 2.5 Flash"
    },
    {
      "id": "gemini-2.5-pro",
      "label": "Gemini 2.5 Pro"
    }
  ],
  "default_model": "gemini-2.5-flash",
  "source": "provider_api",
  "cached": false
}
```

### Not connected provider

```json
{
  "provider": "claude",
  "connected": false,
  "error_code": "PROVIDER_NOT_CONNECTED",
  "message": "Anthropic Claude is not connected. Add an API key to use this provider."
}
```

### Provider API failure

```json
{
  "provider": "gemini",
  "connected": true,
  "error_code": "MODEL_FETCH_FAILED",
  "message": "Could not fetch models from Google Gemini."
}
```

---

## Frontend provider selector behavior

When user selects provider:

```typescript
async function onProviderChange(provider: string) {
  const previousProvider = selectedProvider;
  const previousModel = selectedModel;

  setSelectedProvider(provider);
  setModels([]);
  setModelLoading(true);

  const response = await api.getLLMModels(provider);

  if (!response.connected && response.error_code === "PROVIDER_NOT_CONNECTED") {
    openConnectProviderModal(provider);
    setSelectedProvider(previousProvider);
    setSelectedModel(previousModel);
    setModelLoading(false);
    return;
  }

  if (response.error_code) {
    showToast(response.message);
    setSelectedProvider(previousProvider);
    setSelectedModel(previousModel);
    setModelLoading(false);
    return;
  }

  setModels(response.models);
  setSelectedModel(response.default_model ?? response.models[0]?.id);
  setModelLoading(false);
}
```

---

## Connect provider modal

Create:

```text
apps/frontend/components/settings/connect-provider-modal.tsx
```

or:

```text
apps/frontend/components/chat/connect-provider-dialog.tsx
```

Modal content:

```text
Provider not connected

Anthropic Claude is not connected yet.
Add an API key to use this provider.

Fields:
- API Key
- Base URL optional
- Default model optional

Buttons:
[Cancel] [Connect Provider]
```

After connect:

```text
1. Test API key.
2. Save secret.
3. Fetch model list again.
4. Select default model.
5. Show success toast.
```

If user cancels:

```text
Return selector to previous connected provider.
```

---

## Provider selector validation

Rules:

```text
✅ Do not allow chat send if selected provider is not connected
✅ Do not allow chat send if selected model is empty
✅ Show clear message: “Connect Google Gemini first”
✅ If provider key is missing, open connect modal
✅ If model fetch fails, show error and keep previous provider/model
```

---

# Issue 4 — Chat panel layout / UX

## Problem shown in screenshot

The AI Assistant panel has these problems:

```text
- Chat input goes down near/beyond bottom taskbar
- Scroll area and footer are not well separated
- Chat answer area can overflow awkwardly
- Chat input is too small and not expandable
- Panel needs a fixed header and fixed footer
- Messages should scroll inside a middle area only
```

## Correct layout

The assistant panel should be:

```text
┌──────────────────────────────┐
│ Fixed Header                 │
│ Provider/model selector      │
├──────────────────────────────┤
│ Quick actions                │
├──────────────────────────────┤
│ Scrollable message area      │
│                              │
│ Tool trace / answer cards    │
│                              │
├──────────────────────────────┤
│ Fixed footer                 │
│ High-risk checkbox           │
│ Expandable textarea          │
│ Send button                  │
└──────────────────────────────┘
```

The entire panel height should be:

```css
height: 100dvh;
```

Not plain `100vh`, because browser UI/taskbar can affect viewport behavior.

---

## Recommended Tailwind structure

```tsx
<aside className="fixed right-0 top-0 z-50 flex h-dvh w-[420px] flex-col border-l bg-slate-950">
  <AssistantHeader className="shrink-0" />

  <ProviderModelSelector className="shrink-0" />

  <QuickActions className="shrink-0" />

  <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
    <Messages />
  </div>

  <AssistantFooter className="shrink-0 border-t bg-slate-950 p-3" />
</aside>
```

Important classes:

```text
h-dvh
flex
flex-col
min-h-0
flex-1
overflow-y-auto
shrink-0
```

The key fix is:

```text
min-h-0 flex-1 overflow-y-auto
```

Without `min-h-0`, the message area may push the footer below the screen.

---

## Expandable chat input

Use textarea instead of input.

Behavior:

```text
- Minimum height: 48px
- Maximum height: 160px
- Auto-grow while typing
- If text exceeds max height, textarea scrolls internally
- Enter = send
- Shift+Enter = new line
```

Component:

```text
apps/frontend/components/chat/assistant-input.tsx
```

Expected behavior:

```typescript
function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}
```

Tailwind:

```tsx
<textarea
  className="max-h-40 min-h-12 flex-1 resize-none overflow-y-auto rounded-xl border bg-slate-900 px-3 py-2 text-sm"
/>
```

---

## Send button

Make button fixed next to textarea:

```text
Textarea takes remaining width.
Send button stays right.
Button disabled when:
- message empty
- streaming
- provider not connected
- model missing
```

---

## Scroll behavior

When new tokens arrive:

```text
If user is near bottom:
    auto-scroll to bottom
If user scrolled up:
    do not force scroll
    show “Jump to latest” button
```

Minimum implementation:

```typescript
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
}, [messages, isStreaming]);
```

Better later: detect user scroll position.

---

## Responsive behavior

For desktop:

```text
Panel width: 420px or 440px
```

For smaller screens:

```text
Panel width: 100vw
```

Tailwind:

```tsx
className="w-full sm:w-[420px]"
```

---

# Issue 5 — Chat answer formatting issue

In screenshot, answer is shown as raw table text squeezed in a narrow card.

Improve:

```text
✅ Render Markdown properly
✅ Tables should have horizontal scroll
✅ Long text should wrap
✅ Tool trace and final answer should be visually separate
```

Add wrapper:

```tsx
<div className="prose prose-invert max-w-none overflow-x-auto">
  <Markdown>{content}</Markdown>
</div>
```

If using markdown library:

```bash
npm install react-markdown remark-gfm
```

Then:

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

<ReactMarkdown remarkPlugins={[remarkGfm]}>
  {content}
</ReactMarkdown>
```

---

# Issue 6 — Dashboard empty before data

The first screenshot shows dashboard cards as:

```text
-
0 on · 0 off
No active alarms
No recent events
```

If API is still loading, show skeletons instead of fake zero data.

Rules:

```text
If initial loading:
    show skeleton / loading shimmer

If loaded and count is zero:
    show 0

If error:
    show error badge

If previous data exists and refreshing:
    show previous data + refreshing badge
```

Do not show:

```text
0 on · 0 off
```

until API really returned valid zero counts.

---

# Fix 7 implementation order

## Step 1 — Data persistence and refresh

```text
1. Add inventory/dashboard data store or provider.
2. Keep old data during refresh.
3. Add Refresh button.
4. Add auto-refresh every 2 minutes.
5. Show last updated timestamp.
```

## Step 2 — Health status

```text
1. Fix health endpoint calls.
2. Add timeout.
3. Stop infinite Checking.
4. Show online/offline/degraded correctly.
```

## Step 3 — Provider/model dynamic loading

```text
1. On provider select, call backend models endpoint.
2. If provider not connected, open connect modal.
3. Add connect provider flow.
4. Prevent chat send when provider/model unavailable.
```

## Step 4 — Chat panel layout

```text
1. Convert panel to h-dvh flex-col layout.
2. Make header/provider/quick actions fixed height.
3. Make messages area min-h-0 flex-1 overflow-y-auto.
4. Make footer fixed.
5. Replace input with expandable textarea.
6. Add markdown table rendering and horizontal scroll.
```

## Step 5 — Validation

Run all tests listed below.

---

# Validation test plan

## Test A — Inventory persistence

1. Open Dashboard.
2. Wait until data loads.
3. Go to Settings.
4. Return to Dashboard.

Expected:

```text
Old dashboard data appears immediately.
Small “Refreshing…” indicator appears.
Data updates after API returns.
No blank cards.
```

## Test B — Inventory manual refresh

1. Open Inventory page.
2. Click Refresh.

Expected:

```text
Button changes to Refreshing.
Old table remains visible.
After success, Last updated changes.
If API fails, old table remains and error toast appears.
```

## Test C — Auto refresh

1. Open Inventory page.
2. Wait 2 minutes.

Expected:

```text
Refresh happens automatically.
Old data remains while refreshing.
Last updated timestamp changes.
```

## Test D — System Health

Open System Health page.

Expected:

```text
FastAPI: Online
Agent Engine: Online or Offline
Postgres: Online/Offline/Not configured
Redis: Online/Offline/Not configured
vCenter: Online or Not configured

No item remains Checking forever.
```

## Test E — Provider connected

1. Select Google Gemini.
2. Backend has Gemini API key.

Expected:

```text
Models are fetched.
Model dropdown updates.
Default model selected.
Chat send enabled.
```

## Test F — Provider not connected

1. Select Claude when no Claude API key exists.

Expected:

```text
Connect Provider modal opens.
Message: Claude is not connected.
Fields: API Key, Base URL optional.
Cancel returns to previous provider.
Connect tests/saves key.
```

## Test G — Provider model fetch error

Simulate invalid API key or provider API down.

Expected:

```text
Error toast/card appears.
Previous provider/model remains selected.
Chat send disabled for broken provider.
```

## Test H — Chat panel layout

1. Open AI Assistant panel.
2. Send long prompt.
3. Receive long answer with table.
4. Resize browser vertically.

Expected:

```text
Header remains visible.
Provider/model selectors remain visible.
Message area scrolls.
Footer remains visible above taskbar.
Textarea does not go below screen.
Tables scroll horizontally.
```

## Test I — Expandable input

1. Type multiple lines using Shift+Enter.

Expected:

```text
Textarea grows until max height.
After max height, textarea scrolls internally.
Enter sends.
Shift+Enter creates new line.
```

## Test J — Shortcut prompts

Click:

```text
List Tools
Environment
Powered-off VMs
Datastore Health
Active Alarms
Recent Events
RKE2 VMs
```

Expected:

```text
All use same chat send flow.
No layout break.
No raw JSON shown as final answer.
```

---

# Acceptance checklist

```text
[ ] Dashboard keeps old data during refresh
[ ] Inventory keeps old data during refresh
[ ] Manual Refresh button exists
[ ] Auto-refresh runs every 2 minutes
[ ] Last updated timestamp visible
[ ] Initial loading uses skeleton, not fake zeros
[ ] Refresh failure does not clear old data
[ ] System Health does not stay Checking forever
[ ] Provider change fetches available models
[ ] Provider without API key opens connect modal
[ ] Provider API failure shows clear error
[ ] Chat send disabled if provider/model invalid
[ ] AI Assistant panel uses h-dvh flex-col layout
[ ] Message area scrolls independently
[ ] Footer stays visible above taskbar
[ ] Textarea is expandable
[ ] Enter sends, Shift+Enter adds newline
[ ] Markdown tables render correctly
[ ] Long answers do not break layout
[ ] Shortcut prompts use same SSE chat flow
```

---

# Codex prompt for Fix 7

Use this prompt:

```text
You are working inside my new Kubernetes/RKE2 vCenter Agentic Ops Platform.

Current state:
- Dashboard, Inventory, Monitoring, Settings, Health pages exist.
- AI Assistant panel works with provider/model selector and tool trace.
- vCenter inventory data loads.
- Chat agent now works.
- Frontend path: apps/frontend.
- Backend path: apps/backend.
- FastAPI URL: https://api.dclab.local.
- Frontend URL: https://infra-agent-console.dclab.local.

Fix the following UI/UX and data reliability issues.

ISSUE 1 — Dashboard/inventory data disappears on navigation
Currently when inventory data is collected, then the user navigates away and returns, data is missing and reloads from blank.
Fix:
1. Keep previous dashboard/inventory/monitoring data in a shared frontend cache/store.
2. Do not clear old data when refreshing.
3. Show old data while refresh runs in background.
4. Add manual Refresh button.
5. Add auto-refresh every 2 minutes.
6. Show Last updated timestamp.
7. If refresh fails, keep old data and show warning.
8. Initial page load should show skeletons, not fake zeros.

ISSUE 2 — System Health stuck in Checking
Fix:
1. Wire health checks to real endpoints.
2. Do not leave services as Checking forever.
3. Add request timeout.
4. Show Online/Offline/Degraded/Not configured.
5. vCenter status should use /api/v1/connections/vcenter/status.
6. Agent status should use /api/v1/agent/health if available.
7. Redis/Postgres should show Offline or Not configured if endpoint missing.

ISSUE 3 — Provider/model selector
When user selects a provider/vendor:
1. Send request to backend to get available models for that provider.
2. If provider API key exists, fetch and display models.
3. If provider API key is missing, open a modal asking for API key.
4. Modal should have Connect button.
5. If user cancels, revert to previous provider.
6. If provider is not connected, chat send must be disabled.
7. If model fetch fails, show clear error.
8. Do not silently continue with old model for wrong provider.

Backend endpoints to use or add:
- GET /api/v1/llm/providers
- GET /api/v1/llm/models?provider=<provider>
- GET /api/v1/llm/status?provider=<provider>
- POST /api/v1/connections/llm/provider/test
- POST /api/v1/connections/llm/provider

ISSUE 4 — AI Assistant panel layout
Current panel/input goes down near the taskbar and is not expandable.
Fix:
1. Use fixed right panel with h-dvh and flex-col.
2. Header, provider selector, quick actions, and footer must be shrink-0.
3. Message area must use min-h-0 flex-1 overflow-y-auto.
4. Footer must stay visible above the taskbar.
5. Replace single-line input with expandable textarea.
6. Textarea min height 48px, max height about 160px.
7. Enter sends, Shift+Enter creates newline.
8. Disable send while streaming or provider/model invalid.
9. Render Markdown with tables using react-markdown + remark-gfm.
10. Tables should scroll horizontally inside chat answer cards.
11. Long answers should not break the layout.

Validation:
- Navigate away and back: old data remains visible.
- Manual Refresh keeps old data while loading.
- Auto refresh runs every 2 minutes.
- Health page does not stay Checking.
- Selecting disconnected provider opens connect modal.
- Selecting connected provider fetches models.
- Chat panel footer stays visible.
- Textarea expands.
- Long table answer renders correctly.

Expected result:
A stable operations dashboard where inventory data persists during navigation and refresh, provider/model selection is validated, and the AI Assistant panel has a production-quality layout.
```

---

# Final expected result

After Fix 7:

```text
- Data does not disappear
- Refresh is predictable
- Auto-refresh works
- Health page is meaningful
- Provider/model selection is safe
- Missing API keys are handled clearly
- Chat panel layout is professional
- Input is expandable
- Long answers are readable
```
