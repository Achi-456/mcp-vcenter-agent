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
  const [selectedProvider, setSelectedProvider] = useState('gemini')
  const [apiKey, setApiKey] = useState('')
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [isConfiguring, setIsConfiguring] = useState(false)

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
  const llmStatus = useApiResource(useCallback(() => api.getLlmStatus(), []))
  const llmProviders = useApiResource(useCallback(() => api.getLlmProviders(), []))
  const llmModels = useApiResource(useCallback(() => api.getLlmModels(selectedProvider), [selectedProvider]))
  const resources = useMemo(() => [vcenter, health, mcp, mcpTools, tools, llmStatus, llmProviders, llmModels], [vcenter, health, mcp, mcpTools, tools, llmStatus, llmProviders, llmModels])
  const summary = toolSummary(tools.data)
  const safeTools = safeMcpTools(mcpTools.data)
  const healthData = objectFrom(health.data)
  const providerRows = arrayFrom(llmProviders.data).map((provider) => objectFrom(provider))
  const modelPayload = objectFrom(llmModels.data)
  const modelRows = arrayFrom(modelPayload.models)
    .map((model) => objectFrom(model))
    .slice(0, 30)

  const currentProvider = providerRows.find((p) => p.id === selectedProvider) || { id: selectedProvider, configured: false }
  const llmStatusData = objectFrom(llmStatus.data)
  const runtimeConfigured = llmStatusData.engine_runtime_configured === true
  const backendDiscoveryConfigured = llmStatusData.backend_discovery_configured === true
  const missingRequirements = arrayFrom(llmStatusData.missing_requirements).map((item) => String(item))
  const runtimeEnvKey = selectedProvider === 'openai' ? 'OPENAI_API_KEY' : 'GEMINI_API_KEY'
  const k8sInstructions = [
    `kubectl create secret generic agentic-llm-provider -n agentic-agents --from-literal=${runtimeEnvKey}="<paste-key-here>" --dry-run=client -o yaml | kubectl apply -f -`,
    '',
    'Agent Engine deployment env:',
    '- name: LLM_ENABLED',
    '  value: "true"',
    '- name: LLM_PROVIDER',
    `  value: "${selectedProvider}"`,
    '- name: LLM_MODEL',
    '  value: "<selected-model>"',
    `- name: ${runtimeEnvKey}`,
    '  valueFrom:',
    '    secretKeyRef:',
    '      name: agentic-llm-provider',
    `      key: ${runtimeEnvKey}`,
  ].join('\n')

  async function handleSaveKey() {
    if (!apiKey.trim()) return
    setIsConfiguring(true)
    setActionError(null)
    setActionMessage(null)
    const result = await api.configureLlmProvider(selectedProvider, apiKey)
    if (result.ok) {
      const message = safeDetail(result.data, ['message'], `Provider ${selectedProvider} configured for backend discovery.`)
      setActionMessage(String(message))
      await llmProviders.refresh()
      await llmModels.refresh()
      await llmStatus.refresh()
      setShowKeyModal(false)
      setApiKey('')
    } else {
      setActionError(result.message)
    }
    setIsConfiguring(false)
  }

  function handleProviderChange(provider: string) {
    setSelectedProvider(provider)
    const selected = providerRows.find((item) => item.id === provider)
    if (selected && selected.configured !== true) {
      setApiKey('')
      setShowKeyModal(true)
    }
  }

  async function copyRuntimeInstructions() {
    await navigator.clipboard.writeText(k8sInstructions)
    setActionMessage('Kubernetes runtime instructions copied.')
  }

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
      {showKeyModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ops-navy/60 backdrop-blur-sm">
          <div className="w-full max-md:mx-4 max-w-md rounded-3xl bg-white p-8 shadow-2xl">
            <h2 className="text-xl font-bold text-ops-ink">Configure {selectedProvider}</h2>
            <p className="mt-2 text-sm text-ops-muted">
              {currentProvider.configured
                ? 'An API key is already configured for this provider. Enter a new one to change it.'
                : 'No API key is configured. Please paste your API key below to enable this provider.'}
            </p>
            <div className="mt-6">
              <label className="text-xs font-bold uppercase tracking-widest text-ops-muted">API Key</label>
              <input
                type="password"
                className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-ops-cream px-4 py-3 text-sm text-ops-ink focus:border-ops-navy focus:outline-none"
                placeholder={currentProvider.configured ? '••••••••••••••••' : 'Paste API key here...'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
            <div className="mt-8 flex gap-3">
              <button
                className="flex-1 rounded-xl bg-ops-navy px-4 py-3 text-sm font-semibold text-white hover:bg-ops-steel disabled:opacity-50"
                onClick={handleSaveKey}
                disabled={isConfiguring || !apiKey.trim()}
              >
                {isConfiguring ? 'Saving...' : 'Save API Key'}
              </button>
              <button
                className="flex-1 rounded-xl bg-ops-cream px-4 py-3 text-sm font-semibold text-ops-ink hover:bg-ops-steel/10"
                onClick={() => {
                  setShowKeyModal(false)
                  setApiKey('')
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}

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

        <SectionCard title="LLM Provider" description="Provider/model discovery is fetched by the backend from provider APIs. API keys stay server-side.">
          {llmProviders.error ? <ErrorState title="LLM providers unavailable" message={llmProviders.error} code={llmProviders.errorCode} /> : null}
          {llmModels.error ? <ErrorState title="LLM model discovery unavailable" message={llmModels.error} code={llmModels.errorCode} /> : null}
          <div className="grid gap-4">
            <ConnectionCard
              title="Configured Runtime"
              status={safeStatus(llmStatus.data)}
              rows={[
                { label: 'LLM enabled', value: safeDetail(llmStatus.data, ['llm_enabled'], 'unknown') },
                { label: 'Active provider', value: safeDetail(llmStatus.data, ['active_provider'], 'not configured') },
                { label: 'Active model', value: safeDetail(llmStatus.data, ['active_model'], 'not configured') },
                { label: 'Backend discovery', value: backendDiscoveryConfigured ? 'configured' : 'not configured' },
                { label: 'Agent Engine runtime', value: runtimeConfigured ? 'configured' : 'not configured' },
              ]}
            />
            {!runtimeConfigured ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                <p className="font-semibold">Model discovery may work, but Agent Engine will not use this provider until the runtime secret and deployment environment are configured.</p>
                {missingRequirements.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {missingRequirements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            <div className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
              <div className="flex items-end gap-3">
                <label className="flex-1 text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
                  Provider
                  <select
                    value={selectedProvider}
                    onChange={(event) => handleProviderChange(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-ops-cream px-4 py-2 text-sm normal-case tracking-normal text-ops-ink"
                  >
                    {providerRows.length ? (
                      providerRows.map((provider) => (
                        <option key={String(provider.id)} value={String(provider.id)}>
                          {String(provider.name ?? provider.id)} {provider.configured ? '(configured)' : '(secret missing)'}
                        </option>
                      ))
                    ) : (
                      <option value="gemini">Google Gemini</option>
                    )}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => setShowKeyModal(true)}
                  className="mb-0.5 rounded-xl border border-ops-steel/15 bg-white px-4 py-2 text-sm font-semibold text-ops-ink hover:bg-ops-cream"
                >
                  {currentProvider.configured ? 'Change Key' : 'Configure Key'}
                </button>
              </div>
              <div className="mt-4 flex items-center justify-between gap-3">
                <StatusBadge status={modelPayload.configured === false ? 'not configured' : modelPayload.error ? 'degraded' : 'ready'} />
                <button
                  type="button"
                  onClick={() => void llmModels.refresh()}
                  className="rounded-xl bg-ops-navy px-4 py-2 text-sm font-semibold text-white hover:bg-ops-steel disabled:opacity-50"
                  disabled={llmModels.isRefreshing}
                >
                  {llmModels.isRefreshing ? 'Loading models' : 'Refresh models'}
                </button>
              </div>
              {modelPayload.error ? <p className="mt-3 text-sm text-amber-700">{String(modelPayload.error)}</p> : null}
              {modelPayload.configured === false ? (
                <p className="mt-3 text-sm leading-6 text-ops-muted">Provider secret is not configured on the backend. Add the provider API key via the "Configure Key" button above.</p>
              ) : null}
              <div className="mt-4 max-h-96 overflow-auto rounded-2xl border border-ops-steel/10">
                <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
                  <thead className="bg-ops-cream">
                    <tr>
                      {['Model', 'Display name', 'Input', 'Output'].map((heading) => (
                        <th key={heading} className="border-b border-ops-steel/10 px-3 py-3 font-semibold text-ops-ink">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {modelRows.length ? (
                      modelRows.map((model) => (
                        <tr key={String(model.id ?? model.name)}>
                          <td className="border-b border-ops-steel/10 px-3 py-3 font-mono text-xs text-ops-ink">{String(model.id ?? model.name)}</td>
                          <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{String(model.display_name ?? model.name ?? '—')}</td>
                          <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{String(model.input_token_limit ?? '—')}</td>
                          <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{String(model.output_token_limit ?? '—')}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="px-3 py-6 text-center text-ops-muted">
                          No models returned.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="rounded-2xl border border-ops-info bg-ops-info/20 p-4 text-sm leading-6 text-ops-navy">
              Provider/model selection here is discovery-only. Runtime selection still comes from Engine environment variables so the browser never receives API keys.
            </div>
            <div className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-ops-ink">Agent Engine Runtime Instructions</h3>
                  <p className="mt-1 text-sm leading-6 text-ops-muted">Use these commands/manifests with your own key value. No saved key is shown in the browser.</p>
                </div>
                <button
                  type="button"
                  onClick={() => void copyRuntimeInstructions()}
                  className="rounded-xl border border-ops-steel/15 bg-white px-4 py-2 text-sm font-semibold text-ops-ink hover:bg-ops-cream"
                >
                  Copy instructions
                </button>
              </div>
              <pre className="mt-4 max-h-72 overflow-auto rounded-2xl bg-ops-navy p-4 text-xs leading-5 text-white">
                <code>{k8sInstructions}</code>
              </pre>
            </div>
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
