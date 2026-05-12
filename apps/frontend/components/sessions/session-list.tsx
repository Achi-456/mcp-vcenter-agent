'use client'

import { EmptyState, StatusBadge } from '@/components/ui'
import type { NormalizedSession } from '@/lib/sessions-data'

export function SessionList({
  sessions,
  selectedId,
  onSelect,
}: {
  sessions: NormalizedSession[]
  selectedId: string | null
  onSelect: (session: NormalizedSession) => void
}) {
  if (!sessions.length) {
    return <EmptyState title="No sessions returned" description="The current API did not return session rows." />
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-ops-steel/10">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="bg-ops-cream">
          <tr>
            {['Session ID', 'Created', 'Updated', 'Last Prompt', 'Status', 'Runs/Tools'].map((heading) => (
              <th key={heading} className="border-b border-ops-steel/10 px-3 py-3 font-semibold text-ops-ink">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr
              key={session.id}
              onClick={() => onSelect(session)}
              className={`cursor-pointer hover:bg-ops-cream/70 ${selectedId === session.id ? 'bg-ops-info/20' : ''}`}
            >
              <td className="border-b border-ops-steel/10 px-3 py-3 font-mono text-xs font-semibold text-ops-ink">{session.id}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{session.createdAt}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{session.updatedAt}</td>
              <td className="max-w-sm border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{session.prompt}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <StatusBadge status={session.status} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{session.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
