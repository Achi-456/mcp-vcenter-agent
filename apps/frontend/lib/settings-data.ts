import { arrayFrom, objectFrom, statusValue, stringValue } from './dashboard-data'
import { normalizeTools } from './tools-data'
import type { ToolListResponse } from './types'

const SECRET_KEYS = ['password', 'token', 'secret', 'api_key', 'authorization', 'cookie', 'internal_tool_api_token']

export function redactSensitive(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactSensitive)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => [
      key,
      SECRET_KEYS.some((secretKey) => key.toLowerCase().includes(secretKey)) ? '[REDACTED]' : redactSensitive(item),
    ]),
  )
}

export function safeStatus(value: unknown) {
  return statusValue(value, 'unknown')
}

export function safeDetail(value: unknown, keys: string[], fallback = 'not reported') {
  return stringValue(value, keys, fallback)
}

export function safeMcpTools(payload: unknown) {
  return arrayFrom(payload).map((tool) => objectFrom(tool))
}

export function toolSummary(payload: ToolListResponse | null) {
  const tools = normalizeTools(payload)
  return {
    total: tools.length,
    enabled: tools.filter((tool) => tool.enabled).length,
    implemented: tools.filter((tool) => tool.implemented).length,
    readOnly: tools.filter((tool) => tool.riskLevel === 'read_only').length,
    approvalRequired: tools.filter((tool) => tool.requiresApproval || tool.riskLevel.includes('approval')).length,
    destructive: tools.filter((tool) => tool.riskLevel.includes('destructive') || tool.riskLevel.includes('blocked')).length,
    mcp: tools.filter((tool) => tool.backend === 'mcp').length,
  }
}
