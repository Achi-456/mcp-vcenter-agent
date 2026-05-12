import { MetricCard } from '@/components/ui'
import type { NormalizedTool } from '@/lib/tools-data'

export function ToolSummaryCards({ tools }: { tools: NormalizedTool[] }) {
  const enabled = tools.filter((tool) => tool.enabled).length
  const implemented = tools.filter((tool) => tool.implemented).length
  const readOnly = tools.filter((tool) => tool.riskLevel === 'read_only').length
  const approval = tools.filter((tool) => tool.requiresApproval || tool.riskLevel.includes('approval')).length
  const destructive = tools.filter((tool) => tool.riskLevel.includes('destructive') || tool.riskLevel.includes('blocked')).length
  const mcp = tools.filter((tool) => tool.backend === 'mcp').length

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <MetricCard title="Total tools" value={tools.length} />
      <MetricCard title="Enabled" value={enabled} status="enabled" />
      <MetricCard title="Implemented" value={implemented} status="implemented" />
      <MetricCard title="Read-only" value={readOnly} status="read_only" />
      <MetricCard title="Approval required" value={approval} status="approval" />
      <MetricCard title="MCP tools" value={mcp} status="mcp" />
      {destructive ? <MetricCard title="Destructive/blocked" value={destructive} status="blocked" /> : null}
    </div>
  )
}
