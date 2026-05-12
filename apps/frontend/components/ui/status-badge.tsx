type StatusBadgeProps = {
  status?: string | boolean | null
}

function normalizeStatus(status: StatusBadgeProps['status']) {
  if (typeof status === 'boolean') return status ? 'online' : 'offline'
  return (status ?? 'unknown').toString().toLowerCase().replaceAll('_', ' ')
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = normalizeStatus(status)
  const tone =
    normalized.includes('healthy') || normalized.includes('online') || normalized.includes('ok')
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : normalized.includes('enabled') || normalized.includes('implemented') || normalized.includes('complete')
        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : normalized.includes('checking') || normalized.includes('refreshing') || normalized.includes('safe')
        ? 'border-ops-info bg-ops-info/35 text-ops-navy'
      : normalized.includes('not configured') || normalized.includes('not_configured') || normalized.includes('unknown') || normalized.includes('disabled')
        ? 'border-slate-200 bg-slate-50 text-slate-600'
      : normalized.includes('degraded') || normalized.includes('warning')
        ? 'border-amber-200 bg-amber-50 text-amber-700'
      : normalized.includes('offline') || normalized.includes('error') || normalized.includes('failed') || normalized.includes('blocked') || normalized.includes('critical')
          ? 'border-red-200 bg-red-50 text-red-700'
          : 'border-slate-200 bg-slate-50 text-slate-600'

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}>
      {normalized}
    </span>
  )
}
