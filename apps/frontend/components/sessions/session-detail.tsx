import { EmptyState, SectionCard, StatusBadge } from '@/components/ui'
import { RawToggle } from '@/components/chat'
import type { NormalizedSession } from '@/lib/sessions-data'

export function SessionDetail({ session }: { session: NormalizedSession | null }) {
  if (!session) {
    return <EmptyState title="Select a session" description="Choose a session row to inspect available details." />
  }

  return (
    <SectionCard title="Session Detail" description="Detailed timeline depends on available backend session fields.">
      <div className="space-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold text-ops-muted">Status</span>
          <StatusBadge status={session.status} />
        </div>
        <p className="font-mono text-xs text-ops-ink">{session.id}</p>
        <p className="text-ops-muted">Last prompt: {session.prompt}</p>
        <p className="text-ops-muted">Detailed session timeline is not available from the current API yet.</p>
        <RawToggle raw={JSON.stringify(session.raw, null, 2)} label="View redacted raw session" />
      </div>
    </SectionCard>
  )
}
