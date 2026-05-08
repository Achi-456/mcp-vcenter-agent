export type ChatEventType =
  | "start"
  | "intent"
  | "safety_check"
  | "plan"
  | "tool_call"
  | "tool_result"
  | "tool_cache_hit"
  | "tool_error"
  | "token"
  | "final"
  | "llm_start"
  | "fallback_used"
  | "suggested_next_step"
  | "blocked"
  | "error"
  | "done"

export type ChatEvent =
  | StartEvent
  | IntentEvent
  | SafetyCheckEvent
  | PlanEvent
  | ToolCallEvent
  | ToolResultEvent
  | ToolCacheHitEvent
  | ToolErrorEvent
  | TokenEvent
  | FinalEvent
  | LLMStartEvent
  | FallbackUsedEvent
  | SuggestedNextStepEvent
  | BlockedEvent
  | ErrorEvent
  | DoneEvent

export interface StartEvent {
  type: "start"
  session_id: string
  run_id?: string
}

export interface IntentEvent {
  type: "intent"
  intent: string
  entity?: string | null
}

export interface SafetyCheckEvent {
  type: "safety_check"
  passed: boolean
  risk_level?: string
}

export interface PlanEvent {
  type: "plan"
  goal?: string
  steps: Array<{ label: string; tool?: string; risk_level?: string }>
}

export interface ToolCallEvent {
  type: "tool_call"
  tool: string
  status: "running"
  args?: Record<string, unknown>
}

export interface ToolResultEvent {
  type: "tool_result"
  tool: string
  status: "success" | "error"
  summary?: string
  data_count?: number
  cached?: boolean
}

export interface ToolCacheHitEvent {
  type: "tool_cache_hit"
  tool: string
}

export interface ToolErrorEvent {
  type: "tool_error"
  tool: string
  error_code?: string
  message?: string
}

export interface TokenEvent {
  type: "token"
  content: string
}

export interface FinalEvent {
  type: "final"
  content: string
}

export interface LLMStartEvent {
  type: "llm_start"
  provider: string
  model: string
}

export interface FallbackUsedEvent {
  type: "fallback_used"
  reason: string
}

export interface SuggestedNextStepEvent {
  type: "suggested_next_step"
  content: string
}

export interface BlockedEvent {
  type: "blocked"
  reason: string
  message: string
}

export interface ErrorEvent {
  type: "error"
  message: string
}

export interface DoneEvent {
  type: "done"
}

// ── Message model ───────────────────────────────────────────────────────────

export interface ToolTraceEntry {
  name: string
  status: "running" | "success" | "error"
  summary?: string
  dataCount?: number
  args?: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  createdAt: string
  events?: ChatEvent[]
  toolTrace?: ToolTraceEntry[]
  suggestedNextStep?: string
  blocked?: boolean
  blockedMessage?: string
  error?: boolean
  errorMessage?: string
  llmGenerated?: boolean
  fallbackUsed?: boolean
}

// ── Chat status ─────────────────────────────────────────────────────────────

export type ChatStatus =
  | "ready"
  | "thinking"
  | "planning"
  | "running_tool"
  | "streaming"
  | "blocked"
  | "error"

// ── SSE parsing helpers ─────────────────────────────────────────────────────

export function parseSSELine(line: string): ChatEvent | null {
  if (!line.startsWith("data: ")) return null
  const jsonStr = line.slice(6).trim()
  if (!jsonStr) return null
  try {
    const parsed = JSON.parse(jsonStr) as Record<string, unknown>
    if (!parsed.type || typeof parsed.type !== "string") return null
    return parsed as unknown as ChatEvent
  } catch {
    return null
  }
}
