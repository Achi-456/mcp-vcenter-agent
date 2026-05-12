type LoadingStateProps = {
  label?: string
}

export function LoadingState({ label = 'Loading operational data...' }: LoadingStateProps) {
  return (
    <div className="rounded-2xl border border-ops-steel/10 bg-white p-6 shadow-card">
      <div className="h-2 w-32 animate-pulse rounded-full bg-ops-info/60" />
      <div className="mt-4 h-3 w-3/4 animate-pulse rounded-full bg-slate-100" />
      <div className="mt-3 h-3 w-1/2 animate-pulse rounded-full bg-slate-100" />
      <p className="mt-5 text-sm text-ops-muted">{label}</p>
    </div>
  )
}
