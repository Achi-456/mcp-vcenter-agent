type ToolBadgeProps = {
  label: string
  active?: boolean
}

export function ToolBadge({ label, active = true }: ToolBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${
        active ? 'border-ops-info bg-ops-info/35 text-ops-navy' : 'border-slate-200 bg-slate-50 text-slate-500'
      }`}
    >
      {label}
    </span>
  )
}
