'use client'

import { useCallback, useMemo } from 'react'
import { api } from '@/lib/api'
import { ErrorState, HealthCard, LoadingState, PageHeader, RefreshButton, SectionCard } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'

function serviceStatus(value: unknown) {
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? 'online' : 'offline'
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    if (typeof record.status === 'string') return record.status
    if (typeof record.healthy === 'boolean') return record.healthy ? 'healthy' : 'degraded'
  }
  return 'unknown'
}

export default function HealthPage() {
  const loadHealth = useCallback(() => api.getHealthServices(), [])
  const health = useApiResource(loadHealth)
  const services = useMemo(() => Object.entries(health.data ?? {}), [health.data])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System Health"
        title="Service Status"
        description="FastAPI, Agent Engine, vCenter, MCP, and supporting service status. Checks degrade cleanly instead of staying in an infinite loading state."
        action={<RefreshButton onRefresh={health.refresh} isRefreshing={health.isRefreshing} />}
      />

      {health.isLoading ? <LoadingState label="Checking platform services..." /> : null}
      {health.error ? <ErrorState message={health.error} code={health.errorCode} /> : null}

      <SectionCard title="Services" description="Read from GET /api/v1/health/services.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {services.map(([name, value]) => (
            <HealthCard key={name} name={name} status={serviceStatus(value)} detail="Latest reported service state" />
          ))}
          {!services.length && !health.isLoading ? (
            <HealthCard name="No service rows" status={health.error ? 'degraded' : 'unknown'} detail="The API returned no service entries." />
          ) : null}
        </div>
      </SectionCard>
    </div>
  )
}
