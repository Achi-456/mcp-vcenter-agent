export type ApiSuccess<T> = {
  ok: true
  data: T
  metadata?: Record<string, unknown>
}

export type ApiFailure = {
  ok: false
  error_code?: string
  message: string
  details?: Record<string, unknown>
}

export type ApiEnvelope<T> = ApiSuccess<T> | ApiFailure

export type ServiceHealthMap = Record<string, unknown>

export type ToolSpec = {
  name?: string
  display_name?: string
  description?: string
  backend?: string
  category?: string
  agent?: string
  risk_level?: string
  enabled?: boolean
  implemented?: boolean
  requires_approval?: boolean
  mcp_server?: string
  [key: string]: unknown
}

export type ToolListResponse = ToolSpec[] | { tools?: ToolSpec[]; items?: ToolSpec[]; [key: string]: unknown }

export type ChatEventType =
  | 'start'
  | 'intent'
  | 'safety_check'
  | 'agent_start'
  | 'tool_call'
  | 'tool_result'
  | 'validation'
  | 'final'
  | 'error'
  | 'done'

export type ChatStreamEvent = {
  id: string
  type: ChatEventType
  timestamp: string
  payload: Record<string, unknown>
  raw: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  events?: ChatStreamEvent[]
}
