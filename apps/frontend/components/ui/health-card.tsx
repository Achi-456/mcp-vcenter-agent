import { StatusBadge } from './status-badge'

type HealthCardProps = {
  name: string
  status?: string | boolean | null
  detail?: string
}

export function HealthCard({ name, status, detail }: HealthCardProps) {
  return (
    <article className="rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-ops-ink">{name}</h3>
          {detail ? <p className="mt-2 text-sm text-ops-muted">{detail}</p> : null}
        </div>
        <StatusBadge status={status} />
      </div>
    </article>
  )
}
