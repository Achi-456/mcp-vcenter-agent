type PageHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  action?: React.ReactNode
}

export function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-ops-steel/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
      <div>
        {eyebrow ? <p className="text-xs font-bold uppercase tracking-[0.24em] text-ops-steel">{eyebrow}</p> : null}
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ops-ink">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-muted">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
