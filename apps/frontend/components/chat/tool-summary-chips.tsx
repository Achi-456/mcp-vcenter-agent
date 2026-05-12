import type { ChatStreamEvent } from '@/lib/types'

function toolName(event: ChatStreamEvent) {
  const tool = event.payload.tool
  return typeof tool === 'string' ? tool : null
}

export function toolNamesFromEvents(events: ChatStreamEvent[]) {
  return Array.from(new Set(events.filter((event) => event.type === 'tool_call').map(toolName).filter((tool): tool is string => Boolean(tool))))
}

export function ToolSummaryChips({ events }: { events: ChatStreamEvent[] }) {
  const tools = toolNamesFromEvents(events)
  if (!tools.length) return null

  return (
    <div className="mt-4 border-t border-ops-steel/10 pt-4">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">Tools used</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {tools.map((tool) => (
          <span key={tool} className="rounded-full border border-ops-info bg-ops-info/30 px-2.5 py-1 font-mono text-xs font-semibold text-ops-navy">
            {tool}
          </span>
        ))}
      </div>
    </div>
  )
}
