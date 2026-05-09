# Fix 6 — Chat UI Events + SSE Rendering

## Focus Area

This step focuses on the **frontend chat experience** for the AI Assistant.

The backend/agent may already emit SSE events such as:

- `start`
- `intent`
- `safety_check`
- `plan`
- `tool_call`
- `tool_result`
- `token`
- `final`
- `suggested_next_step`
- `blocked`
- `error`
- `done`

Fix 6 makes the UI correctly parse those events and render them as a professional infrastructure-operations chat experience.

---

## What this fixes

| # | Issue | Fix |
|---|---|---|
| 1 | SSE stream is parsed as plain text only | Add structured SSE event parser |
| 2 | Tool calls are not visually clear | Add `ToolCallCard` |
| 3 | Tool results are not easy to read | Add `ToolResultCard` |
| 4 | Agent plan is hidden or mixed into text | Add `PlanCard` |
| 5 | No clear thinking/streaming state | Add typing indicator |
| 6 | Session handling is weak | Add session ID display + new session button |
| 7 | Blocked/error events look like normal messages | Render blocked/error cards separately |
| 8 | Shortcut prompts and manual prompts use inconsistent flow | Route both through the same SSE chat flow |

---

## Target user experience

When the user asks:

```text
get details for esxi01.dclab.com
```

The UI should show:

```text
User:
get details for esxi01.dclab.com

Assistant status:
Thinking...

Plan:
1. Identify object type
2. Run safety check
3. Use get_host_details
4. Summarize host details

Tool Call:
get_host_details
args: {"host_name":"esxi01.dclab.com"}

Tool Result:
success — Found ESXi host esxi01.dclab.com

Assistant:
I found ESXi host esxi01.dclab.com. No action was taken.

| Property | Value |
|---|---|
| Connection State | connected |
| Power State | poweredOn |
| Version | ESXi 7.0.3 |
...
```

For a risky request:

```text
turn esxi01.dclab.com maintenance mode
```

The UI should show:

```text
Safety Check:
Blocked — approval_required

Assistant:
This is a high-risk host operation and is disabled in Phase 1.4.
No action was taken.
```

---

## Files to focus on

Expected frontend files:

```text
apps/frontend/
├── hooks/
│   └── use-sse-chat.ts
├── components/
│   └── chat/
│       ├── ai-assistant-panel.tsx
│       ├── plan-card.tsx
│       ├── tool-call-card.tsx
│       ├── tool-result-card.tsx
│       ├── typing-indicator.tsx
│       ├── blocked-card.tsx
│       ├── error-card.tsx
│       └── session-header.tsx
└── lib/
    ├── api.ts
    └── chat-events.ts
```

If these files do not exist, create them.

---

## Step 1 — Define typed chat events

Create:

```text
apps/frontend/lib/chat-events.ts
```

Add TypeScript event types:

```typescript
export type ChatEventType =
  | "start"
  | "intent"
  | "safety_check"
  | "plan"
  | "tool_call"
  | "tool_result"
  | "token"
  | "final"
  | "suggested_next_step"
  | "blocked"
  | "error"
  | "done";

export type ChatEvent =
  | StartEvent
  | IntentEvent
  | SafetyCheckEvent
  | PlanEvent
  | ToolCallEvent
  | ToolResultEvent
  | TokenEvent
  | FinalEvent
  | SuggestedNextStepEvent
  | BlockedEvent
  | ErrorEvent
  | DoneEvent;

export interface StartEvent {
  type: "start";
  session_id: string;
  run_id?: string;
}

export interface IntentEvent {
  type: "intent";
  intent: string;
  target_type?: string;
  entity?: string;
  confidence?: number;
}

export interface SafetyCheckEvent {
  type: "safety_check";
  risk_level: "read_only" | "low_risk" | "approval_required" | "destructive";
  allowed: boolean;
  reason?: string;
}

export interface PlanEvent {
  type: "plan";
  goal?: string;
  steps: Array<{
    label: string;
    tool?: string;
    risk_level?: string;
  }>;
}

export interface ToolCallEvent {
  type: "tool_call";
  tool: string;
  status: "running";
  args?: Record<string, unknown>;
}

export interface ToolResultEvent {
  type: "tool_result";
  tool: string;
  status: "success" | "error";
  summary?: string;
  data_count?: number;
  error_code?: string;
  message?: string;
}

export interface TokenEvent {
  type: "token";
  content: string;
}

export interface FinalEvent {
  type: "final";
  content: string;
}

export interface SuggestedNextStepEvent {
  type: "suggested_next_step";
  content: string;
}

export interface BlockedEvent {
  type: "blocked";
  reason: string;
  message: string;
  risk_level?: string;
}

export interface ErrorEvent {
  type: "error";
  error_code?: string;
  message: string;
}

export interface DoneEvent {
  type: "done";
}
```

---

## Step 2 — Implement robust SSE parser

Update:

```text
apps/frontend/hooks/use-sse-chat.ts
```

The hook must support both common SSE formats:

### Format A — Standard SSE event name

```text
event: tool_call
data: {"tool":"get_host_details","status":"running"}
```

### Format B — Data contains type

```text
data: {"type":"tool_call","tool":"get_host_details","status":"running"}
```

The parser should normalize both into:

```typescript
{
  type: "tool_call",
  tool: "get_host_details",
  status: "running"
}
```

---

## Step 3 — Hook state model

The hook should expose:

```typescript
{
  messages,
  events,
  currentSessionId,
  currentRunId,
  status,
  isStreaming,
  sendMessage,
  stop,
  newSession,
  error
}
```

Recommended status values:

```typescript
type ChatStatus =
  | "ready"
  | "thinking"
  | "planning"
  | "running_tool"
  | "streaming"
  | "blocked"
  | "error";
```

---

## Step 4 — Message model

Use a clean message structure:

```typescript
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  events?: ChatEvent[];
  suggestedNextStep?: string;
  blocked?: boolean;
  error?: boolean;
}
```

When a user sends a prompt:

```text
1. Add user message immediately.
2. Add empty assistant message.
3. Stream tokens into assistant message.
4. Attach tool events to that assistant message.
5. Mark completed when done event arrives.
```

---

## Step 5 — PlanCard component

Create:

```text
apps/frontend/components/chat/plan-card.tsx
```

Purpose:

```text
Show the agent's plan before or during tool execution.
```

Props:

```typescript
interface PlanCardProps {
  goal?: string;
  steps: Array<{
    label: string;
    tool?: string;
    risk_level?: string;
  }>;
}
```

UI requirements:

```text
- Small card inside assistant message
- Uses slate border/background
- Shows goal
- Shows numbered steps
- Shows tool badge if step uses a tool
- Shows risk badge if provided
```

Example display:

```text
Plan
Goal: Get ESXi host details

1. Classify target object
2. Run safety check
3. Call get_host_details
4. Summarize result
```

---

## Step 6 — ToolCallCard component

Create:

```text
apps/frontend/components/chat/tool-call-card.tsx
```

Props:

```typescript
interface ToolCallCardProps {
  tool: string;
  args?: Record<string, unknown>;
  status?: "running";
}
```

UI requirements:

```text
- Show tool name in monospace
- Show "running" badge
- Show args as small JSON block
- Use cyan/blue accent for running
```

Example:

```text
Tool Call
get_host_details
running

args:
{
  "host_name": "esxi01.dclab.com"
}
```

---

## Step 7 — ToolResultCard component

Create:

```text
apps/frontend/components/chat/tool-result-card.tsx
```

Props:

```typescript
interface ToolResultCardProps {
  tool: string;
  status: "success" | "error";
  summary?: string;
  data_count?: number;
  error_code?: string;
  message?: string;
}
```

UI requirements:

```text
- Success = emerald badge
- Error = red badge
- Show summary
- Show data_count if available
- Show error_code and message for failures
```

Example success:

```text
Tool Result
get_host_details
success

Found ESXi host esxi01.dclab.com
```

Example error:

```text
Tool Result
get_vm_details
error

VM_NOT_FOUND
No VM named esxi01.dclab.com was found.
```

---

## Step 8 — TypingIndicator component

Create:

```text
apps/frontend/components/chat/typing-indicator.tsx
```

Show when:

```text
status = thinking
status = planning
status = running_tool
status = streaming
```

Suggested labels:

```text
thinking       → Assistant is thinking...
planning       → Planning tool execution...
running_tool   → Running vCenter tool...
streaming      → Writing answer...
```

Keep it subtle and professional.

---

## Step 9 — SessionHeader component

Create:

```text
apps/frontend/components/chat/session-header.tsx
```

It should show:

```text
- Current session ID
- Current provider/model
- Status badge
- New Session button
```

Example:

```text
Session: session-01HX...
Provider: Gemini
Model: gemini-2.5-flash
Status: Ready
[New Session]
```

New Session button behavior:

```text
1. Clear messages and events
2. Reset current session ID to null
3. Reset status to ready
4. Keep provider/model selection
```

---

## Step 10 — BlockedCard and ErrorCard

Create:

```text
apps/frontend/components/chat/blocked-card.tsx
apps/frontend/components/chat/error-card.tsx
```

Blocked card should show:

```text
Blocked high-risk action
Reason: approval_required
No action was taken.
```

Error card should show:

```text
Tool or agent error
Error code
Message
```

Do not display raw stack traces.

---

## Step 11 — Update AI Assistant panel

Update:

```text
apps/frontend/components/chat/ai-assistant-panel.tsx
```

Requirements:

```text
1. Use the updated useSSEChat hook.
2. Render SessionHeader at top.
3. Render messages.
4. For each assistant message, render:
   - PlanCard if plan event exists
   - ToolCallCard for tool_call events
   - ToolResultCard for tool_result events
   - BlockedCard for blocked events
   - ErrorCard for error events
   - assistant final Markdown content
   - suggested next step card
5. Show TypingIndicator while streaming.
6. New Session button must work.
7. Existing prompt shortcut buttons should call sendMessage(prompt).
```

---

## Step 12 — Update shortcut prompts

Shortcut buttons should no longer directly render local context endpoint results.

They should call the same chat flow:

```typescript
sendMessage("Give me an environment overview.");
sendMessage("Show powered-off VMs.");
sendMessage("Analyze datastore health and highlight critical datastores.");
sendMessage("Summarize active alarms.");
sendMessage("Show recent vCenter events.");
sendMessage("Show my RKE2-related VMs.");
```

This ensures:

```text
Shortcut prompt → chat SSE → intent → tools → answer
```

Same behavior as manual prompt.

---

## Step 13 — API client endpoint

Confirm frontend sends chat requests to:

```text
POST /api/v1/chat/stream
```

Request body:

```json
{
  "message": "get details for esxi01.dclab.com",
  "session_id": "optional",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "allow_high_risk": false,
  "page_context": {
    "page": "dashboard",
    "selected_tab": "overview"
  }
}
```

---

## Step 14 — Parser validation tests

Create a small parser test if test framework exists.

Test input:

```text
event: tool_call
data: {"tool":"get_host_details","status":"running"}
```

Expected:

```json
{
  "type": "tool_call",
  "tool": "get_host_details",
  "status": "running"
}
```

Test input:

```text
data: {"type":"tool_result","tool":"get_host_details","status":"success","summary":"Found host"}
```

Expected:

```json
{
  "type": "tool_result",
  "tool": "get_host_details",
  "status": "success",
  "summary": "Found host"
}
```

Test malformed JSON:

```text
data: not-json
```

Expected:

```text
Parser does not crash.
Error is captured or ignored safely.
```

---

## Step 15 — Manual SSE test

Run:

```powershell
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"get details for esxi01.dclab.com","provider":"gemini","model":"gemini-2.5-flash","allow_high_risk":false}' `
  https://api.dclab.local/api/v1/chat/stream
```

Expected events:

```text
start
intent
safety_check
plan
tool_call
tool_result
token
final
suggested_next_step
done
```

---

## Step 16 — Browser validation test

Open:

```text
https://infra-agent-console.dclab.local
```

Open AI Assistant panel and test:

### Test 1 — New Session

```text
Click New Session
```

Expected:

```text
Messages cleared.
Session ID cleared or regenerated on next send.
Provider/model remains selected.
Status = Ready.
```

### Test 2 — Host details

Prompt:

```text
get details for esxi01.dclab.com
```

Expected UI:

```text
- User message visible
- Session ID visible
- Typing indicator appears
- PlanCard appears
- ToolCallCard: get_host_details
- ToolResultCard: success
- Final assistant answer renders
- Suggested next step appears
```

### Test 3 — VM details

Prompt:

```text
inspect roshellevm02
```

Expected:

```text
ToolCallCard: get_vm_details
ToolResultCard: success or VM_NOT_FOUND
No fake N/A table if not found
```

### Test 4 — Blocked action

Prompt:

```text
turn esxi01.dclab.com maintenance mode
```

Expected:

```text
BlockedCard appears.
No tool call for maintenance mode.
No vCenter change.
Final answer says no action was taken.
```

### Test 5 — Tool list

Prompt:

```text
list down all the tools you have
```

Expected:

```text
Plan/tool trace visible.
Final answer groups tools by category.
Risky tools marked disabled/approval required.
```

### Test 6 — Shortcut prompts

Click each shortcut:

```text
Environment overview
Powered-off VMs
Datastore health
Active alarms
Recent events
RKE2 VMs
```

Expected:

```text
Each shortcut creates a normal user message.
Each goes through SSE.
Each shows tool trace and final answer.
```

---

## Step 17 — Visual acceptance criteria

The chat UI is accepted only when:

```text
[ ] SSE parser supports event-name and data-type formats
[ ] PlanCard renders plan events
[ ] ToolCallCard renders running tools
[ ] ToolResultCard renders success/error results
[ ] Typing indicator appears during streaming
[ ] Session ID is visible
[ ] New Session button clears conversation
[ ] Prompt shortcuts use same chat flow
[ ] Blocked risky actions have separate UI
[ ] Errors have separate UI
[ ] Raw JSON is not shown as normal assistant text
[ ] Tool trace is readable and professional
[ ] Final answer is readable Markdown
```

---

## Step 18 — Build checks

Run:

```bash
cd apps/frontend
npm run lint
npm run build
```

After deploy:

```bash
kubectl rollout status deploy/nextjs -n agentic-app
kubectl logs deploy/nextjs -n agentic-app --tail=100
```

---

## Step 19 — Argo CD validation

Check:

```bash
kubectl get pods -n agentic-app
kubectl get ingress -n agentic-app
```

Expected:

```text
nextjs pod running
fastapi pod running
AI Assistant panel loads without frontend console errors
```

---

## What Fix 6 does NOT implement

| Not included | Reason |
|---|---|
| New backend tools | Covered in Fix 5 |
| LLM answer generation | Covered in Fix 4 |
| vCenter persistent session | Covered in Fix 2 |
| Host-vs-VM classifier | Covered in Fix 3 |
| Real power/delete/snapshot actions | Future approval workflow phase |

---

## Final expected result

After Fix 6:

```text
The AI Assistant UI will behave like a real operations console:
- structured plan
- visible tool calls
- visible tool results
- streamed answer
- clear blocked/error states
- session display
- new session control
- prompt shortcuts routed through the same agent flow
```

This makes the frontend ready for a production-style vCenter AI assistant.
