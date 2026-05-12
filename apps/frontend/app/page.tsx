'use client'

import { useCallback, useMemo } from 'react'
import { api } from '@/lib/api'
import { HealthCard, LoadingState, MetricCard, PageHeader, RefreshButton, SectionCard } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'
import type { ServiceHealthMap } from '@/lib/types'

function countServices(data: ServiceHealthMap | null, predicate: (value: unknown) => boolean) {
  if (!data) return 0
  return Object.values(data).filter(predicate).length
}

function statusFromValue(value: unknown) {
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? 'online' : 'offline'
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    if (typeof record.status === 'string') return record.status
    if (typeof record.healthy === 'boolean') return record.healthy ? 'healthy' : 'degraded'
  }
  return 'unknown'
}

export default function DashboardPage() {
  const loadHealth = useCallback(() => api.getHealthServices(), [])
  const health = useApiResource(loadHealth)

  const services = useMemo(() => Object.entries(health.data ?? {}), [health.data])
  const healthyCount = countServices(health.data, (value) => {
    const status = statusFromValue(value).toLowerCase()
    return status.includes('healthy') || status.includes('online') || status.includes('ok')
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations Overview"
        title="Dashboard"
        description="A vCenter-style summary for infrastructure health, diagnostic readiness, and safe automation posture."
        action={<RefreshButton onRefresh={health.refresh} isRefreshing={health.isRefreshing} />}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Services" value={services.length || '—'} subtitle="Reported by FastAPI health services" status="live" />
        <MetricCard title="Healthy" value={healthyCount || '—'} subtitle="Online or healthy service checks" status="status" />
        <MetricCard title="Agent Health" value="Ready" subtitle="Chat routing handled by Agent Engine" status="phase 9a" />
        <MetricCard title="MCP Posture" value="Safe" subtitle="Metadata/status only in UI foundation" status="read-only" />
      </div>

      {health.isLoading ? <LoadingState /> : null}
      {health.error ? (
        <SectionCard title="Health service unavailable" description={health.error}>
          <p className="text-sm text-ops-muted">Existing dashboard cards stay visible while the API is unreachable.</p>
        </SectionCard>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <SectionCard
          title="Environment Overview"
          description="Phase 9A wires health only. Inventory, alarms, events, and datastore summaries are added in later UI subphases."
        >
          <div className="grid gap-3 md:grid-cols-2">
            {services.slice(0, 6).map(([name, value]) => (
              <HealthCard key={name} name={name} status={statusFromValue(value)} detail="Service status from /api/v1/health/services" />
            ))}
            {!services.length && !health.isLoading ? (
              <HealthCard name="FastAPI health" status={health.error ? 'degraded' : 'unknown'} detail="No service rows returned yet." />
            ) : null}
          </div>
        </SectionCard>

        <SectionCard title="AI Suggested Checks" description="Prompt examples for the Phase 9B assistant experience.">
          <div className="space-y-3 text-sm text-ops-muted">
            <p className="rounded-xl bg-ops-cream px-4 py-3 font-mono text-ops-ink">summarize vCenter health</p>
            <p className="rounded-xl bg-ops-cream px-4 py-3 font-mono text-ops-ink">critical datastores?</p>
            <p className="rounded-xl bg-ops-cream px-4 py-3 font-mono text-ops-ink">test MCP</p>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
