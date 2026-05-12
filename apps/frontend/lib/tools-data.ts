import type { ToolListResponse, ToolSpec } from './types'

export type NormalizedTool = {
  name: string
  displayName: string
  description: string
  backend: string
  category: string
  agent: string
  riskLevel: string
  enabled: boolean
  implemented: boolean
  requiresApproval: boolean
  mcpServer: string
  raw: ToolSpec
}

export function normalizeTools(payload: ToolListResponse | null): NormalizedTool[] {
  const tools = Array.isArray(payload) ? payload : Array.isArray(payload?.tools) ? payload.tools : Array.isArray(payload?.items) ? payload.items : []
  return tools.map((tool) => ({
    name: tool.name ?? 'unnamed_tool',
    displayName: tool.display_name ?? tool.name ?? 'Unnamed Tool',
    description: tool.description ?? '',
    backend: tool.backend ?? 'unknown',
    category: tool.category ?? 'Uncategorized',
    agent: tool.agent ?? '—',
    riskLevel: tool.risk_level ?? 'unknown',
    enabled: tool.enabled === true,
    implemented: tool.implemented === true,
    requiresApproval: tool.requires_approval === true,
    mcpServer: tool.mcp_server ?? '—',
    raw: tool,
  }))
}
