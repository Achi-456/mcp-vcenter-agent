'use client'

import Link from 'next/link'
import { useCallback, useMemo } from 'react'
import { api } from '@/lib/api'
import {
  arrayFrom,
  firstUpdated,
  formatDate,
  hasFailures,
  isRefreshing,
  numberValue,
  objectFrom,
  refreshAll,
  statusValue,
  stringValue,
} from '@/lib/dashboard-data'
import { EmptyState, ErrorState, HealthCard, LoadingState, MetricCard, PageHeader, RefreshButton, SectionCard, StatusBadge } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'

const REFRESH_INTERVAL_MS = 120000

function countByStatus(items: unknown[], statuses: string[]) {
  return items.filter((item) => {
    const status = statusValue(item).toLowerCase()
    return statuses.some((expected) => status.includes(expected))
  }).length
}

function poweredOnCount(vms: unknown[]) {
  return vms.filter((vm) => stringValue(vm, ['power_state', 'powerState', 'status', 'state'], '').toLowerCase().includes('poweredon')).length
}

function field(item: unknown, keys: string[], fallback = '—') {
  return stringValue(item, keys, fallback)
}

function percent(item: unknown) {
  const direct = numberValue(item, ['used_percent', 'usedPercent', 'usage_percent', 'usagePercent', 'used_pct'], -1)
  if (direct >= 0) return `${direct.toFixed(1)}%`
  return field(item, ['used_percent', 'usedPercent', 'usage_percent', 'usagePercent', 'used_pct'])
}

function freeGb(item: unknown) {
  const direct = numberValue(item, ['free_gb', 'freeGb', 'freeGB'], -1)
  if (direct >= 0) return direct.toFixed(1)
  return field(item, ['free_gb', 'freeGb', 'freeGB', 'free'])
}

function CompactTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-ops-steel/10">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="bg-ops-cream">
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-ops-cream/60">
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`} className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
  const health = useApiResource(useCallback(() => api.getHealthServices(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const environment = useApiResource(useCallback(() => api.getEnvironment(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const vmsResource = useApiResource(useCallback(() => api.getVms(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const hostsResource = useApiResource(useCallback(() => api.getHosts(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const datastoresResource = useApiResource(useCallback(() => api.getDatastores(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const datastoreHealth = useApiResource(useCallback(() => api.getDatastoreHealth(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const alarmsResource = useApiResource(useCallback(() => api.getAlarms(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const eventsResource = useApiResource(useCallback(() => api.getEvents(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const mcpStatus = useApiResource(useCallback(() => api.getMcpDefaultStatus(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })

  const resources = useMemo(
    () => [health, environment, vmsResource, hostsResource, datastoresResource, datastoreHealth, alarmsResource, eventsResource, mcpStatus],
    [health, environment, vmsResource, hostsResource, datastoresResource, datastoreHealth, alarmsResource, eventsResource, mcpStatus],
  )

  const vms = arrayFrom(vmsResource.data)
  const hosts = arrayFrom(hostsResource.data)
  const datastores = arrayFrom(datastoresResource.data)
  const datastoreHealthRows = arrayFrom(datastoreHealth.data)
  const alarms = arrayFrom(alarmsResource.data)
  const events = arrayFrom(eventsResource.data)
  const environmentRecord = objectFrom(environment.data)
  const serviceRecord = objectFrom(health.data)
  const latestUpdate = firstUpdated(resources)
  const partialFailure = hasFailures(resources)
  const refreshing = isRefreshing(resources)

  const criticalDatastores = datastoreHealthRows.filter((item) => statusValue(item).toLowerCase().includes('critical'))
  const warningDatastores = datastoreHealthRows.filter((item) => statusValue(item).toLowerCase().includes('warning'))
  const healthyDatastores = datastoreHealthRows.filter((item) => {
    const status = statusValue(item).toLowerCase()
    return status.includes('healthy') || status.includes('ok')
  })

  const vcenterStatus = stringValue(serviceRecord.vcenter, ['status'], statusValue(serviceRecord.vcenter, environment.error ? 'degraded' : 'unknown'))
  const agentStatus = stringValue(serviceRecord.agent_engine, ['status'], statusValue(serviceRecord.agent_engine, 'unknown'))
  const mcpServerStatus = statusValue(mcpStatus.data, mcpStatus.error ? 'degraded' : 'unknown')

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations Overview"
        title="Dashboard"
        description="vCenter operations overview and AI platform status."
        action={<RefreshButton onRefresh={() => refreshAll(resources)} isRefreshing={refreshing} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={partialFailure ? 'degraded' : refreshing ? 'refreshing' : 'healthy'} />
        <span>Auto-refresh every 2 minutes.</span>
        <span>Last updated: {formatDate(latestUpdate)}</span>
        {refreshing ? <span className="font-semibold text-ops-steel">Refreshing old data in place...</span> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="vCenter status" value={vcenterStatus} subtitle="From health/environment signals" status={partialFailure ? 'degraded' : 'live'} />
        <MetricCard title="Total VMs" value={vms.length || numberValue(environment.data, ['vm_count', 'vms'], '—' as never)} subtitle="Inventory VMs" />
        <MetricCard title="Powered On VMs" value={poweredOnCount(vms) || '—'} subtitle="Best-effort power state count" />
        <MetricCard title="Hosts" value={hosts.length || numberValue(environment.data, ['host_count', 'hosts'], '—' as never)} subtitle="ESXi hosts" />
        <MetricCard title="Datastores" value={datastores.length || numberValue(environment.data, ['datastore_count', 'datastores'], '—' as never)} subtitle="Inventory datastores" />
        <MetricCard title="Active Alarms" value={alarms.length || '—'} subtitle="Monitoring alarms" status={alarms.length ? 'review' : 'clear'} />
        <MetricCard title="Critical Datastores" value={criticalDatastores.length} subtitle={`${warningDatastores.length} warning`} status={criticalDatastores.length ? 'critical' : 'clear'} />
        <MetricCard title="Recent Events" value={events.length || '—'} subtitle="Last 50 event query" />
        <MetricCard title="Agent Engine" value={agentStatus} subtitle="Chat runtime status" />
        <MetricCard title="MCP Server" value={mcpServerStatus} subtitle="Safe MCP status tools" />
      </div>

      {resources.every((resource) => resource.isLoading) ? <LoadingState label="Loading dashboard resources..." /> : null}

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Environment Overview" description="Counts and vCenter metadata from environment and inventory endpoints.">
          {environment.error ? <ErrorState message={environment.error} code={environment.errorCode} /> : null}
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <HealthCard name="VM count" status="ok" detail={String(vms.length || numberValue(environment.data, ['vm_count', 'vms'], 0))} />
            <HealthCard name="Host count" status="ok" detail={String(hosts.length || numberValue(environment.data, ['host_count', 'hosts'], 0))} />
            <HealthCard name="Datastore count" status="ok" detail={String(datastores.length || numberValue(environment.data, ['datastore_count', 'datastores'], 0))} />
            <HealthCard name="Critical datastore count" status={criticalDatastores.length ? 'critical' : 'healthy'} detail={String(criticalDatastores.length)} />
            <HealthCard name="Warning datastore count" status={warningDatastores.length ? 'warning' : 'healthy'} detail={String(warningDatastores.length)} />
            <HealthCard
              name="vCenter version/build"
              status={vcenterStatus}
              detail={`${stringValue(environmentRecord, ['version', 'vcenter_version'])} / ${stringValue(environmentRecord, ['build', 'vcenter_build'])}`}
            />
          </div>
        </SectionCard>

        <SectionCard title="Suggested AI Checks" description="Copyable prompts for the AI Assistant.">
          <div className="grid gap-2">
            {[
              'summarize vCenter health',
              'critical datastores?',
              'show active alarms',
              'show recent events',
              'check roshellevm02',
              'test MCP',
            ].map((prompt) => (
              <Link
                key={prompt}
                href={`/chat?prompt=${encodeURIComponent(prompt)}`}
                className="rounded-xl bg-ops-cream px-4 py-3 font-mono text-xs text-ops-ink ring-1 ring-ops-steel/10 transition hover:bg-ops-info/20"
              >
                {prompt}
              </Link>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Datastore Health" description="Compact datastore health summary from /api/v1/context/datastore-health.">
        {datastoreHealth.error ? <ErrorState message={datastoreHealth.error} code={datastoreHealth.errorCode} /> : null}
        <div className="mb-5 grid gap-3 md:grid-cols-3">
          <MetricCard title="Healthy" value={healthyDatastores.length} status="healthy" />
          <MetricCard title="Warning" value={warningDatastores.length} status="warning" />
          <MetricCard title="Critical" value={criticalDatastores.length} status={criticalDatastores.length ? 'critical' : 'clear'} />
        </div>
        {criticalDatastores.length ? (
          <CompactTable
            columns={['Datastore', 'Used %', 'Free GB', 'Accessible', 'Status']}
            rows={criticalDatastores.slice(0, 5).map((item) => [
              field(item, ['name', 'datastore', 'datastore_name']),
              percent(item),
              freeGb(item),
              field(item, ['accessible', 'is_accessible']),
              statusValue(item),
            ])}
          />
        ) : (
          <EmptyState title="No critical datastores reported" description="Datastore health returned no critical rows for this refresh window." />
        )}
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Active Alarms" description="Top active alarms from /api/v1/monitoring/alarms.">
          {alarmsResource.error ? <ErrorState message={alarmsResource.error} code={alarmsResource.errorCode} /> : null}
          {alarms.length ? (
            <CompactTable
              columns={['Name/Alarm', 'Target/Object', 'Severity/Status', 'Time']}
              rows={alarms.slice(0, 5).map((item) => [
                field(item, ['name', 'alarm', 'alarm_name', 'description']),
                field(item, ['target', 'object', 'entity', 'vm', 'host']),
                field(item, ['severity', 'status', 'state']),
                field(item, ['time', 'created_at', 'timestamp']),
              ])}
            />
          ) : (
            <EmptyState title="No active alarms returned" description="The alarms endpoint returned no active alarm rows." />
          )}
        </SectionCard>

        <SectionCard title="Recent Events" description="Top recent events from /api/v1/monitoring/events?limit=50.">
          {eventsResource.error ? <ErrorState message={eventsResource.error} code={eventsResource.errorCode} /> : null}
          {events.length ? (
            <CompactTable
              columns={['Time', 'Object', 'Event', 'User']}
              rows={events.slice(0, 5).map((item) => [
                field(item, ['time', 'created_at', 'timestamp']),
                field(item, ['object', 'entity', 'target', 'vm', 'host']),
                field(item, ['event', 'message', 'description', 'type']),
                field(item, ['user', 'username', 'user_name']),
              ])}
            />
          ) : (
            <EmptyState title="No recent events returned" description="The events endpoint returned no rows for the current refresh window." />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
