import { StatusBadge } from '@/components/ui'

type ConnectionCardProps = {
  title: string
  status: string
  rows: Array<{ label: string; value: string }>
  action?: React.ReactNode
}

export function ConnectionCard({ title, status, rows, action }: ConnectionCardProps) {
  return (
    <section className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="font-semibold text-ops-ink">{title}</h3>
        <StatusBadge status={status} />
      </div>
      <div className="mt-4 space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-start justify-between gap-4 border-b border-ops-steel/10 py-2 text-sm">
            <span className="font-semibold text-ops-muted">{row.label}</span>
            <span className="text-right text-ops-ink">{row.value}</span>
          </div>
        ))}
      </div>
      {action ? <div className="mt-4">{action}</div> : null}
    </section>
  )
}
