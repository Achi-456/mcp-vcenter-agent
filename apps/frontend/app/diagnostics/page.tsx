import { EmptyState, PageHeader, SectionCard, ToolBadge } from '@/components/ui'

const backends = ['pyVmomi', 'govc', 'vSphere REST', 'Compare', 'MCP Safe Status']

export default function DiagnosticsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Diagnostics"
        title="Read-only Diagnostic Workbench"
        description="A safe workspace for pyVmomi, govc, vSphere REST, compare flows, and MCP status checks. No destructive actions or raw command execution."
      />

      <SectionCard title="Diagnostic Backends" description="Phase 9A creates the safe tab structure. Interactive forms are implemented in Phase 9E.">
        <div className="flex flex-wrap gap-2">
          {backends.map((backend) => (
            <ToolBadge key={backend} label={backend} />
          ))}
        </div>
        <div className="mt-5">
          <EmptyState
            title="Diagnostics forms are scheduled for Phase 9E"
            description="MCP remains safe-status only. The UI will not expose arbitrary MCP execution, shell, govc command strings, or infrastructure mutations."
          />
        </div>
      </SectionCard>
    </div>
  )
}
