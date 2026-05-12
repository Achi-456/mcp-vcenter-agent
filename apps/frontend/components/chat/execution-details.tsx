'use client'

import { useState } from 'react'
import type { ChatStreamEvent } from '@/lib/types'
import { ChatEventCard } from './event-cards'

export function ExecutionDetails({ events }: { events: ChatStreamEvent[] }) {
  const [open, setOpen] = useState(false)
  const runId = events.find((event) => event.type === 'start')?.payload.run_id

  if (!events.length) return null

  return (
    <div className="mt-4 border-t border-ops-steel/10 pt-4">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="rounded-xl border border-ops-steel/15 bg-white px-3 py-2 text-sm font-semibold text-ops-steel transition hover:bg-ops-cream"
      >
        {open ? 'Hide execution details' : 'View execution details'}
      </button>

      {open ? (
        <div className="mt-4 space-y-3 rounded-2xl border border-ops-steel/10 bg-ops-cream/70 p-4">
          {typeof runId === 'string' ? <p className="font-mono text-xs text-ops-muted">Run ID: {runId}</p> : null}
          {events
            .filter((event) => event.type !== 'final' && event.type !== 'done')
            .map((event) => (
              <ChatEventCard key={event.id} event={event} />
            ))}
        </div>
      ) : null}
    </div>
  )
}
