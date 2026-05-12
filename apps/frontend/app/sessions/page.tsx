import { EmptyState, PageHeader, SectionCard } from '@/components/ui'

export default function SessionsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Sessions"
        title="Investigation Sessions"
        description="A future timeline for chat sessions, tool traces, and audit-friendly investigation summaries."
      />

      <SectionCard title="Session History" description="Minimal Version 1 scaffold.">
        <EmptyState
          title="No session list wired yet"
          description="Phase 9F will connect this page if stable session APIs are available. Until then, chat state stays on the AI Assistant page."
        />
      </SectionCard>
    </div>
  )
}
