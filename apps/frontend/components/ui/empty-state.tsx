type EmptyStateProps = {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-ops-steel/25 bg-white/70 p-8 text-center">
      <h3 className="font-semibold text-ops-ink">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-ops-muted">{description}</p>
    </div>
  )
}
