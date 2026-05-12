import type { ChatStreamEvent } from '@/lib/types'

function value(payload: Record<string, unknown>, key: string, fallback = '') {
  const item = payload[key]
  if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') return String(item)
  return fallback
}

export function progressText(event: ChatStreamEvent | undefined) {
  if (!event) return 'Waiting for Agent Engine...'
  if (event.type === 'start') return 'Starting session...'
  if (event.type === 'intent') return 'Understanding request...'
  if (event.type === 'safety_check') return event.payload.allowed === false ? 'Request blocked by safety policy.' : 'Safety check passed.'
  if (event.type === 'agent_start') return 'Starting diagnostic agent...'
  if (event.type === 'tool_call') return `Checking ${value(event.payload, 'tool', 'tool')}...`
  if (event.type === 'tool_result') return `Received result from ${value(event.payload, 'tool', 'tool')}.`
  if (event.type === 'validation') return 'Validating result...'
  if (event.type === 'final') return 'Answer ready.'
  if (event.type === 'error') return 'Something went wrong.'
  if (event.type === 'done') return 'Complete.'
  return 'Working...'
}

export function LiveProgress({ events }: { events: ChatStreamEvent[] }) {
  const visibleEvents = events.filter((event) => event.type !== 'done')
  const latest = visibleEvents.at(-1)

  return (
    <div className="rounded-xl border border-ops-info/60 bg-ops-info/20 px-4 py-3 text-sm text-ops-navy">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-ops-steel" />
        <span className="font-semibold">{progressText(latest)}</span>
      </div>
      {visibleEvents.length > 1 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {visibleEvents.slice(-4).map((event) => (
            <span key={event.id} className="rounded-full bg-white/70 px-2 py-1 text-[11px] font-semibold text-ops-steel">
              {progressText(event)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
