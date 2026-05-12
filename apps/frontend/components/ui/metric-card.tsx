type MetricCardProps = {
  title: string
  value: string | number
  subtitle?: string
  status?: string
}

export function MetricCard({ title, value, subtitle, status }: MetricCardProps) {
  return (
    <article className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-ops-muted">{title}</p>
        {status ? <span className="rounded-full bg-ops-info/35 px-2 py-1 text-xs font-semibold text-ops-navy">{status}</span> : null}
      </div>
      <div className="mt-4 text-3xl font-bold tracking-tight text-ops-ink">{value}</div>
      {subtitle ? <p className="mt-2 text-sm text-ops-muted">{subtitle}</p> : null}
    </article>
  )
}
