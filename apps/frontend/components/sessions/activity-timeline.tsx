import { EmptyState, StatusBadge } from '@/components/ui'
import type { NormalizedActivity } from '@/lib/sessions-data'

export function ActivityTimeline({ activities }: { activities: NormalizedActivity[] }) {
  if (!activities.length) {
    return <EmptyState title="No audit activity returned" description="Audit events are unavailable or empty from the current API." />
  }

  return (
    <div className="space-y-3">
      {activities.slice(0, 20).map((activity) => (
        <article key={activity.id} className="rounded-2xl border border-ops-steel/10 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-ops-ink">{activity.action}</p>
              <p className="mt-1 text-xs text-ops-muted">{activity.timestamp}</p>
            </div>
            <StatusBadge status={activity.status} />
          </div>
          <p className="mt-3 text-sm text-ops-muted">{activity.summary}</p>
          <p className="mt-2 text-xs text-ops-muted">Source: {activity.actor}</p>
        </article>
      ))}
    </div>
  )
}
