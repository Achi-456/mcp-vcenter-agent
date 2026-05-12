'use client'

import { useCallback, useMemo } from 'react'
import { api } from '@/lib/api'
import {
  firstUpdated,
  formatDate,
  hasFailures,
  isRefreshing,
  objectFrom,
  refreshAll,
  statusValue,
  stringValue,
} from '@/lib/dashboard-data'
import { ErrorState, HealthCard, LoadingState, PageHeader, RefreshButton, SectionCard, StatusBadge } from '@/components/ui'
import { RawToggle } from '@/components/chat'
import { useApiResource } from '@/hooks/use-api-resource'

const REFRESH_INTERVAL_MS = 120000

function serviceStatus(value: unknown) {
  return statusValue(value)
}

function detailText(value: unknown) {
  const record = objectFrom(value)
  return (
    stringValue(record, ['message', 'detail', 'details', 'description'], '') ||
    `Status: ${serviceStatus(value)}`
  )
}

function serviceValue(services: Record<string, unknown>, names: string[]) {
  for (const name of names) {
    if (services[name] !== undefined) return services[name]
  }
  return null
}

export default function HealthPage() {
  const health = useApiResource(useCallback(() => api.getHealthServices(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const vcenter = useApiResource(useCallback(() => api.getVcenterStatus(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const mcp = useApiResource(useCallback(() => api.getMcpDefaultStatus(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })

  const resources = useMemo(() => [health, vcenter, mcp], [health, vcenter, mcp])
  const services = objectFrom(health.data)
  const latestUpdate = firstUpdated(resources)
  const refreshing = isRefreshing(resources)
  const degraded = hasFailures(resources)

  const serviceCards = [
    {
      name: 'FastAPI',
      value: serviceValue(services, ['fastapi', 'api', 'backend']),
      description: 'API gateway and frontend data source',
    },
    {
      name: 'Agent Engine',
      value: serviceValue(services, ['agent_engine', 'agent', 'engine']),
      description: 'LangGraph runtime for chat stream',
    },
    {
      name: 'Postgres',
      value: serviceValue(services, ['postgres', 'database', 'db']),
      description: 'Session, audit, and platform persistence',
    },
    {
      name: 'Redis',
      value: serviceValue(services, ['redis', 'cache']),
      description: 'Cache and runtime support service',
    },
    {
      name: 'vCenter',
      value: vcenter.data ?? serviceValue(services, ['vcenter', 'vcenter_connection']),
      description: 'vCenter credential and connectivity status',
    },
    {
      name: 'MCP Gateway',
      value: serviceValue(services, ['mcp_gateway', 'mcp']),
      description: 'FastAPI MCP gateway metadata/status path',
    },
    {
      name: 'MCP Server',
      value: mcp.data,
      description: 'Default safe MCP server status',
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System Health"
        title="System Health"
        description="Runtime status of AgenticOps services."
        action={<RefreshButton onRefresh={() => refreshAll(resources)} isRefreshing={refreshing} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={degraded ? 'degraded' : refreshing ? 'checking' : 'healthy'} />
        <span>Auto-refresh every 2 minutes.</span>
        <span>Last checked: {formatDate(latestUpdate)}</span>
        {refreshing ? <span className="font-semibold text-ops-steel">Refreshing...</span> : null}
      </div>

      {resources.every((resource) => resource.isLoading) ? <LoadingState label="Checking platform services..." /> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {serviceCards.map((service) => (
          <HealthCard
            key={service.name}
            name={service.name}
            status={service.value ? serviceStatus(service.value) : degraded ? 'degraded' : 'unknown'}
            detail={`${service.description}. ${service.value ? detailText(service.value) : 'No direct service row returned.'}`}
          />
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="vCenter Status" description="Read from GET /api/v1/connections/vcenter/status.">
          {vcenter.error ? <ErrorState message={vcenter.error} code={vcenter.errorCode} /> : null}
          <div className="space-y-3 text-sm text-ops-muted">
            <div className="flex items-center justify-between gap-3">
              <span>Status</span>
              <StatusBadge status={vcenter.data ? serviceStatus(vcenter.data) : vcenter.error ? 'degraded' : 'unknown'} />
            </div>
            <p>Configured: {stringValue(vcenter.data, ['configured', 'is_configured'], 'unknown')}</p>
            <p>Host/URL: {stringValue(vcenter.data, ['host', 'url', 'vcenter_host', 'vcenter_url'], 'not reported')}</p>
          </div>
        </SectionCard>

        <SectionCard title="MCP Status" description="Read from GET /api/v1/mcp/servers/default/status.">
          {mcp.error ? <ErrorState message={mcp.error} code={mcp.errorCode} /> : null}
          <div className="space-y-3 text-sm text-ops-muted">
            <div className="flex items-center justify-between gap-3">
              <span>Status</span>
              <StatusBadge status={mcp.data ? serviceStatus(mcp.data) : mcp.error ? 'degraded' : 'unknown'} />
            </div>
            <p>Server: {stringValue(mcp.data, ['server_id', 'id', 'name'], 'default')}</p>
            <p>Tools: {stringValue(mcp.data, ['tool_count', 'tools_count', 'tools'], 'not reported')}</p>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Details" description="Raw health details are hidden by default and must not contain secrets.">
        <div className="space-y-3">
          {health.error ? <ErrorState message={health.error} code={health.errorCode} /> : null}
          <div className="overflow-x-auto rounded-xl border border-ops-steel/10">
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead className="bg-ops-cream">
                <tr>
                  <th className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">Service</th>
                  <th className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">Status</th>
                  <th className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">Details</th>
                </tr>
              </thead>
              <tbody>
                {serviceCards.map((service) => (
                  <tr key={service.name}>
                    <td className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">{service.name}</td>
                    <td className="border-b border-ops-steel/10 px-3 py-2">
                      <StatusBadge status={service.value ? serviceStatus(service.value) : 'unknown'} />
                    </td>
                    <td className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">
                      {service.value ? detailText(service.value) : 'No direct payload returned.'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <RawToggle
            label="View raw health payloads"
            raw={JSON.stringify(
              {
                health_services: health.data,
                vcenter_status: vcenter.data,
                mcp_default_status: mcp.data,
              },
              null,
              2,
            )}
          />
        </div>
      </SectionCard>
    </div>
  )
}
