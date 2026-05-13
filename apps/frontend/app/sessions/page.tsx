'use client'

import { useCallback, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { firstUpdated, formatDate, refreshAll } from '@/lib/dashboard-data'
import { normalizeActivities, normalizeSessions, type NormalizedSession } from '@/lib/sessions-data'
import { ActivityTimeline, SessionDetail, SessionList } from '@/components/sessions'
import { ErrorState, PageHeader, RefreshButton, SectionCard, StatusBadge } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'

export default function SessionsPage() {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [selectedSession, setSelectedSession] = useState<NormalizedSession | null>(null)
  const sessions = useApiResource(useCallback(() => api.getSessions(), []))
  const audit = useApiResource(useCallback(() => api.getAuditEvents(), []))
  const resources = useMemo(() => [sessions, audit], [sessions, audit])
  const sessionRows = useMemo(() => normalizeSessions(sessions.data), [sessions.data])
  const activityRows = useMemo(() => normalizeActivities(audit.data), [audit.data])
  const filteredSessions = useMemo(
    () =>
      sessionRows.filter((session) => {
        const query = search.toLowerCase().trim()
        return !query || [session.id, session.prompt, session.status].some((value) => value.toLowerCase().includes(query))
      }),
    [search, sessionRows],
  )

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Sessions"
        title="Sessions"
        description="Review assistant sessions and recent tool activity."
        action={<RefreshButton onRefresh={() => refreshAll(resources)} isRefreshing={resources.some((resource) => resource.isRefreshing)} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={resources.some((resource) => resource.error) ? 'degraded' : 'healthy'} />
        <span>Last checked: {formatDate(firstUpdated(resources))}</span>
      </div>

      <SectionCard title="Session History" description="If the sessions endpoint is unavailable, this page degrades cleanly.">
        <div className="mb-4">
          <label className="text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
            Search
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search session ID or prompt..."
              className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-ops-cream px-4 py-2 text-sm normal-case tracking-normal text-ops-ink"
            />
          </label>
        </div>
        {sessions.error ? (
          <ErrorState title="Sessions API unavailable" message="Session history is not available from the current API yet." code={sessions.errorCode} />
        ) : null}
        <SessionList
          sessions={filteredSessions}
          selectedId={selectedSession?.id ?? null}
          onSelect={(session) => {
            setSelectedSession(session)
            router.push(`/chat?session_id=${encodeURIComponent(session.id)}`)
          }}
        />
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <SessionDetail session={selectedSession} />
        <SectionCard title="Recent Activity" description="Audit timeline if /api/v1/audit/events is available.">
          {audit.error ? (
            <ErrorState title="Audit events unavailable" message="Recent audit activity is not available from the current API yet." code={audit.errorCode} />
          ) : null}
          <ActivityTimeline activities={activityRows} />
        </SectionCard>
      </div>
    </div>
  )
}
