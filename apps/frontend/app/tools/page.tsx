'use client'

import { useCallback, useMemo } from 'react'
import { api } from '@/lib/api'
import { ErrorState, LoadingState, PageHeader, RefreshButton, RiskBadge, SectionCard, StatusBadge, ToolBadge } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'
import type { ToolListResponse, ToolSpec } from '@/lib/types'

function normalizeTools(payload: ToolListResponse | null): ToolSpec[] {
  if (!payload) return []
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload.tools)) return payload.tools
  if (Array.isArray(payload.items)) return payload.items
  return []
}

export default function ToolsPage() {
  const loadTools = useCallback(() => api.getTools(), [])
  const toolsState = useApiResource(loadTools)
  const tools = useMemo(() => normalizeTools(toolsState.data), [toolsState.data])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Tool Registry"
        description="Platform-wide catalog of governed tools. Phase 9A shows metadata only and never exposes arbitrary MCP execution."
        action={<RefreshButton onRefresh={toolsState.refresh} isRefreshing={toolsState.isRefreshing} />}
      />

      {toolsState.isLoading ? <LoadingState label="Loading tool registry..." /> : null}
      {toolsState.error ? <ErrorState message={toolsState.error} code={toolsState.errorCode} /> : null}

      <SectionCard title="Registered Tools" description="Read from GET /api/v1/tools.">
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-ops-muted">
                <th className="border-b border-ops-steel/10 px-3 py-3">Tool</th>
                <th className="border-b border-ops-steel/10 px-3 py-3">Backend</th>
                <th className="border-b border-ops-steel/10 px-3 py-3">Risk</th>
                <th className="border-b border-ops-steel/10 px-3 py-3">Enabled</th>
                <th className="border-b border-ops-steel/10 px-3 py-3">Implemented</th>
                <th className="border-b border-ops-steel/10 px-3 py-3">Approval</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((tool, index) => (
                <tr key={`${tool.name ?? 'tool'}-${index}`} className="hover:bg-ops-cream/70">
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <div className="font-mono text-xs font-semibold text-ops-ink">{tool.name ?? tool.display_name ?? 'unnamed_tool'}</div>
                    {tool.description ? <div className="mt-1 max-w-md text-xs text-ops-muted">{tool.description}</div> : null}
                  </td>
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <ToolBadge label={tool.backend ?? 'unknown'} />
                  </td>
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <RiskBadge risk={tool.risk_level} />
                  </td>
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <StatusBadge status={tool.enabled === true ? 'enabled' : 'disabled'} />
                  </td>
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <StatusBadge status={tool.implemented === true ? 'implemented' : 'not implemented'} />
                  </td>
                  <td className="border-b border-ops-steel/10 px-3 py-3">
                    <StatusBadge status={tool.requires_approval === true ? 'approval required' : 'not required'} />
                  </td>
                </tr>
              ))}
              {!tools.length && !toolsState.isLoading ? (
                <tr>
                  <td className="px-3 py-8 text-center text-sm text-ops-muted" colSpan={6}>
                    No tool metadata returned yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
