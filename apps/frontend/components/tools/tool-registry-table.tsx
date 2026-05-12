import { EmptyState, RiskBadge, StatusBadge, ToolBadge } from '@/components/ui'
import type { NormalizedTool } from '@/lib/tools-data'

export function ToolRegistryTable({ tools }: { tools: NormalizedTool[] }) {
  if (!tools.length) {
    return <EmptyState title="No tools match the current filters" description="Adjust search or filters to inspect ToolRegistry metadata." />
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-ops-steel/10">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="bg-ops-cream">
          <tr>
            {['Tool Name', 'Display Name', 'Backend', 'Category', 'Agent', 'Risk Level', 'Enabled', 'Implemented', 'Requires Approval', 'MCP Server', 'Description'].map(
              (heading) => (
                <th key={heading} className="border-b border-ops-steel/10 px-3 py-3 font-semibold text-ops-ink">
                  {heading}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => (
            <tr key={tool.name} className="hover:bg-ops-cream/70">
              <td className="border-b border-ops-steel/10 px-3 py-3 font-mono text-xs font-semibold text-ops-ink">{tool.name}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{tool.displayName}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <ToolBadge label={tool.backend} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{tool.category}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{tool.agent}</td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <RiskBadge risk={tool.riskLevel} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <StatusBadge status={tool.enabled ? 'enabled' : 'disabled'} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <StatusBadge status={tool.implemented ? 'implemented' : 'not implemented'} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3">
                <StatusBadge status={tool.requiresApproval ? 'approval required' : 'not required'} />
              </td>
              <td className="border-b border-ops-steel/10 px-3 py-3 text-ops-muted">{tool.mcpServer}</td>
              <td className="max-w-md border-b border-ops-steel/10 px-3 py-3 text-xs leading-5 text-ops-muted">{tool.description || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
