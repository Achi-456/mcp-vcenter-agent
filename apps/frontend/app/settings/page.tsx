import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/ui'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Settings"
        title="Configuration"
        description="Safe configuration visibility for vCenter, LLM provider, MCP, and UI preferences. Secrets are never displayed."
      />

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="vCenter Connection">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-ops-muted">Credential source</span>
            <StatusBadge status="secret reference only" />
          </div>
        </SectionCard>
        <SectionCard title="MCP Internal Status">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-ops-muted">Safe tools</span>
            <StatusBadge status="metadata only" />
          </div>
        </SectionCard>
      </div>

      <EmptyState
        title="Editable settings are not part of Phase 9A"
        description="Later UI phases may add safe test-connection controls, but passwords, API keys, and internal tokens will never be rendered."
      />
    </div>
  )
}
