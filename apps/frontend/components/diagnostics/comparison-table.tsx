import { StatusBadge } from '@/components/ui'

type ComparisonRow = {
  field: string
  pyvmomi: string
  govc: string
  status: string
}

export function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  if (!rows.length) return null
  return (
    <div className="overflow-x-auto rounded-xl border border-ops-steel/10">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="bg-ops-cream">
          <tr>
            {['Field', 'pyVmomi', 'govc', 'Status'].map((heading) => (
              <th key={heading} className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field}>
              <td className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">{row.field}</td>
              <td className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">{row.pyvmomi}</td>
              <td className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">{row.govc}</td>
              <td className="border-b border-ops-steel/10 px-3 py-2">
                <StatusBadge status={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
