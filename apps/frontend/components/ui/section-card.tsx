type SectionCardProps = {
  title: string
  description?: string
  children: React.ReactNode
}

export function SectionCard({ title, description, children }: SectionCardProps) {
  return (
    <section className="min-w-0 rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-ops-ink">{title}</h2>
        {description ? <p className="mt-1 text-sm text-ops-muted">{description}</p> : null}
      </div>
      {children}
    </section>
  )
}
