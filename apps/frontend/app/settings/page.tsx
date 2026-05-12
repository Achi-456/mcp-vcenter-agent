'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { arrayFrom, firstUpdated, formatDate, objectFrom, refreshAll } from '@/lib/dashboard-data'
import { redactSensitive, safeDetail, safeMcpTools, safeStatus, toolSummary } from '@/lib/settings-data'
import { normalizeTools } from '@/lib/tools-data'
import { ConnectionCard, PreferenceToggle, SettingsActionCard } from '@/components/settings'
import { ErrorState, MetricCard, PageHeader, RefreshButton, SectionCard, StatusBadge, ToolBadge } from '@/components/ui'
import { RawToggle } from '@/components/chat'
import { useApiResource } from '@/hooks/use-api-resource'

type Preferences = {
  compactTables: boolean
  showRawDetails: boolean
  autoRefresh: boolean
}

const DEFAULT_PREFS: Preferences = {
  compactTables: false,
  showRawDetails: false,
  autoRefresh: true,
}

const PREF_KEY = 'agenticops-ui-preferences'

export default function SettingsPage() {
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFS)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(PREF_KEY)
      if (stored) setPreferences({ ...DEFAULT_PREFS, ...JSON.parse(stored) })
    } catch {
      setPreferences(DEFAULT_PREFS)
    }
  }, [])

  function updatePreference<K extends keyof Preferences>(key: K, value: Preferences[K]) {
    const next = { ...preferences, [key]: value }
    setPreferences(next)
    window.localStorage.setItem(PREF_KEY, JSON.stringify(next))
  }

  const vcenter = useApiResource(useCallback(() => api.getVcenterStatus(), []))
  const health = useApiResource(useCallback(() => api.getHealthServices(), []))
  const mcp = useApiResource(useCallback(() => api.getMcpDefaultStatus(), []))
  const mcpTools = useApiResource(useCallback(() => api.getMcpTools(), []))
  const tools = useApiResource(useCallback(() => api.getTools(), []))
  const resources = useMemo(() => [vcenter, health, mcp, mcpTools, tools], [vcenter, health, mcp, mcpTools, tools])
  const summary = toolSummary(tools.data)
  const safeTools = safeMcpTools(mcpTools.data)
  const healthData = objectFrom(health.data)

  async function runAction(kind: 'test' | 'reconnect') {
    if (kind === 'reconnect') {
      const confirmed = window.confirm('Reconnect refreshes the backend vCenter session only. It does not modify inventory or perform vCenter actions. Continue?')
      if (!confirmed) return
    }

    setActionLoading(true)
    setActionMessage(null)
    setActionError(null)
    const response = kind === 'test' ? await api.testVcenterConnection() : await api.reconnectVcenter()
    if (response.ok) {
      setActionMessage(kind === 'test' ? 'vCenter connection test completed.' : 'vCenter reconnect request completed.')
      await vcenter.refresh()
    } else {
      setActionError(response.message)
    }
    setActionLoading(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Settings"
        title="Settings"
        description="Runtime configuration, connection status, and safe platform controls."
        action={<RefreshButton onRefresh={() => refreshAll(resources)} isRefreshing={resources.some((resource) => resource.isRefreshing)} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={resources.some((resource) => resource.error) ? 'degraded' : 'healthy'} />
        <span>Last checked: {formatDate(firstUpdated(resources))}</span>
      </div>

      {actionError ? <ErrorState title="Settings action failed" message={actionError} code="ACTION_FAILED" /> : null}
      {actionMessage ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">{actionMessage}</div> : null}

      <div className="grid gap-5 xl:grid-cols-2">
        <ConnectionCard
          title="vCenter Connection"
          status={vcenter.error ? 'degraded' : safeStatus(vcenter.data)}
          rows={[
            { label: 'Configured', value: safeDetail(vcenter.data, ['configured', 'is_configured'], 'unknown') },
            { label: 'Host / URL', value: safeDetail(vcenter.data, ['host', 'url', 'vcenter_host', 'vcenter_url'], 'not reported') },
            { label: 'Username hint', value: safeDetail(vcenter.data, ['username', 'user', 'user_hint'], 'not reported') },
            { label: 'Secret reference', value: safeDetail(vcenter.data, ['secret_ref', 'secret_name'], 'Kubernetes Secret') },
            { label: 'Last checked', value: formatDate(vcenter.lastUpdated) },
          ]}
          action={
            <div className="grid gap-3 md:grid-cols-2">
              <SettingsActionCard title="Test Connection" description="Validate backend vCenter connectivity using configured secret references." buttonLabel="Test Connection" disabled={actionLoading} onAction={() => runAction('test')} />
              <SettingsActionCard title="Reconnect" description="Refresh backend vCenter session only. Does not modify inventory." buttonLabel="Reconnect" disabled={actionLoading} onAction={() => runAction('reconnect')} tone="secondary" />
            </div>
          }
        />

        <ConnectionCard
          title="Agent Engine"
          status={safeStatus(healthData.agent_engine ?? healthData.agent ?? healthData.engine)}
          rows={[
            { label: 'FastAPI', value: safeStatus(healthData.fastapi ?? healthData.api ?? healthData.backend) },
            { label: 'Agent Engine', value: safeStatus(healthData.agent_engine ?? healthData.agent ?? healthData.engine) },
            { label: 'Chat availability', value: safeStatus(healthData.chat ?? healthData.agent_engine ?? healthData.agent) },
          ]}
          action={
            <Link href="/chat" className="inline-flex rounded-xl bg-ops-navy px-4 py-2 text-sm font-semibold text-white hover:bg-ops-steel">
              Open AI Assistant
            </Link>
          }
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <SectionCard title="MCP Status" description="Metadata/status only. Internal MCP execution is backend-restricted and not exposed directly in the browser.">
          {mcp.error ? <ErrorState message={mcp.error} code={mcp.errorCode} /> : null}
          <div className="grid gap-3 md:grid-cols-2">
            <ConnectionCard
              title="Default MCP Server"
              status={mcp.error ? 'degraded' : safeStatus(mcp.data)}
              rows={[
                { label: 'Server', value: safeDetail(mcp.data, ['server_id', 'id', 'name'], 'default') },
                { label: 'Tools count', value: String(safeTools.length || safeDetail(mcp.data, ['tool_count', 'tools_count'], 'not reported')) },
                { label: 'Last checked', value: formatDate(mcp.lastUpdated) },
              ]}
            />
            <div className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
              <h3 className="font-semibold text-ops-ink">Safe MCP Tools</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {safeTools.length
                  ? safeTools.map((tool, index) => <ToolBadge key={index} label={safeDetail(tool, ['name'], 'mcp tool')} />)
                  : normalizeTools(tools.data)
                      .filter((tool) => tool.backend === 'mcp')
                      .map((tool) => <ToolBadge key={tool.name} label={tool.name} />)}
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="LLM Provider">
          <div className="rounded-2xl border border-ops-info bg-ops-info/20 p-4 text-sm leading-6 text-ops-navy">
            Deterministic routing is active. LLM provider configuration UI is planned later. No API key is shown or stored in the browser.
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Tool Governance Summary" description="Read-only ToolRegistry summary from /api/v1/tools.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
          <MetricCard title="Total" value={summary.total} />
          <MetricCard title="Enabled" value={summary.enabled} />
          <MetricCard title="Implemented" value={summary.implemented} />
          <MetricCard title="Read-only" value={summary.readOnly} />
          <MetricCard title="Approval required" value={summary.approvalRequired} />
          <MetricCard title="Destructive/blocked" value={summary.destructive} />
          <MetricCard title="MCP" value={summary.mcp} />
        </div>
        <Link href="/tools" className="mt-4 inline-flex rounded-xl bg-ops-navy px-4 py-2 text-sm font-semibold text-white hover:bg-ops-steel">
          Open Tools
        </Link>
      </SectionCard>

      <SectionCard title="UI Preferences" description="Frontend-only preferences stored in localStorage.">
        <div className="grid gap-3 md:grid-cols-3">
          <PreferenceToggle label="Compact tables" description="Use denser table spacing where supported." checked={preferences.compactTables} onChange={(value) => updatePreference('compactTables', value)} />
          <PreferenceToggle label="Show raw details by default" description="Preference saved for future detail panels." checked={preferences.showRawDetails} onChange={(value) => updatePreference('showRawDetails', value)} />
          <PreferenceToggle label="Auto-refresh enabled" description="Preference saved for future refresh controls." checked={preferences.autoRefresh} onChange={(value) => updatePreference('autoRefresh', value)} />
        </div>
      </SectionCard>

      <SectionCard title="Redacted Runtime Payloads" description="Raw details are hidden and sensitive keys are redacted.">
        <RawToggle
          label="View redacted settings payloads"
          raw={JSON.stringify(redactSensitive({ vcenter: vcenter.data, health: health.data, mcp: mcp.data, tools: tools.data }), null, 2)}
        />
      </SectionCard>
    </div>
  )
}
