type RiskBadgeProps = {
  risk?: string | null
}

export function RiskBadge({ risk }: RiskBadgeProps) {
  const normalized = (risk ?? 'unknown').toLowerCase()
  const tone =
    normalized === 'read_only'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : normalized.includes('approval') || normalized.includes('low')
        ? 'border-amber-200 bg-amber-50 text-amber-700'
        : normalized.includes('destructive') || normalized.includes('blocked')
          ? 'border-red-200 bg-red-50 text-red-700'
          : 'border-slate-200 bg-slate-50 text-slate-600'

  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}>{normalized}</span>
}
