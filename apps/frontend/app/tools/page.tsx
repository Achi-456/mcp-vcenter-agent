'use client'

import { useCallback, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dashboard-data'
import { normalizeTools } from '@/lib/tools-data'
import { ErrorState, LoadingState, PageHeader, RefreshButton, SectionCard, StatusBadge } from '@/components/ui'
import { ToolFilters, ToolRegistryTable, ToolSummaryCards } from '@/components/tools'
import { useApiResource } from '@/hooks/use-api-resource'

export default function ToolsPage() {
  const [search, setSearch] = useState('')
  const [backend, setBackend] = useState('all')
  const [risk, setRisk] = useState('all')
  const [enabled, setEnabled] = useState('all')
  const [implemented, setImplemented] = useState('all')
  const toolsState = useApiResource(useCallback(() => api.getTools(), []))
  const tools = useMemo(() => normalizeTools(toolsState.data), [toolsState.data])

  const filteredTools = useMemo(
    () =>
      tools.filter((tool) => {
        const query = search.toLowerCase().trim()
        const searchMatch =
          !query ||
          [tool.name, tool.displayName, tool.description].some((value) => value.toLowerCase().includes(query))
        const backendMatch = backend === 'all' || tool.backend === backend
        const riskMatch = risk === 'all' || tool.riskLevel === risk
        const enabledMatch = enabled === 'all' || (enabled === 'enabled' ? tool.enabled : !tool.enabled)
        const implementedMatch = implemented === 'all' || (implemented === 'implemented' ? tool.implemented : !tool.implemented)
        return searchMatch && backendMatch && riskMatch && enabledMatch && implementedMatch
      }),
    [backend, enabled, implemented, risk, search, tools],
  )

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Tools"
        description="ToolRegistry governance and backend capability map. Metadata only; no execute buttons."
        action={<RefreshButton onRefresh={toolsState.refresh} isRefreshing={toolsState.isRefreshing} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={toolsState.error ? 'degraded' : toolsState.isRefreshing ? 'refreshing' : 'healthy'} />
        <span>Last updated: {formatDate(toolsState.lastUpdated)}</span>
        {toolsState.isRefreshing ? <span className="font-semibold text-ops-steel">Refreshing old data in place...</span> : null}
      </div>

      {toolsState.isLoading ? <LoadingState label="Loading ToolRegistry metadata..." /> : null}
      {toolsState.error ? <ErrorState message={toolsState.error} code={toolsState.errorCode} /> : null}

      <ToolSummaryCards tools={tools} />

      <SectionCard title="Registered Tools" description={`Showing ${filteredTools.length} of ${tools.length} tools from /api/v1/tools.`}>
        <div className="space-y-4">
          <ToolFilters
            search={search}
            onSearchChange={setSearch}
            backend={backend}
            onBackendChange={setBackend}
            risk={risk}
            onRiskChange={setRisk}
            enabled={enabled}
            onEnabledChange={setEnabled}
            implemented={implemented}
            onImplementedChange={setImplemented}
          />
          <ToolRegistryTable tools={filteredTools} />
        </div>
      </SectionCard>
    </div>
  )
}
