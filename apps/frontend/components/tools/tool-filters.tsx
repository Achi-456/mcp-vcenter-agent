'use client'

type ToolFiltersProps = {
  search: string
  onSearchChange: (value: string) => void
  backend: string
  onBackendChange: (value: string) => void
  risk: string
  onRiskChange: (value: string) => void
  enabled: string
  onEnabledChange: (value: string) => void
  implemented: string
  onImplementedChange: (value: string) => void
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 block rounded-xl border border-ops-steel/15 bg-white px-3 py-2 text-sm normal-case tracking-normal text-ops-ink"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export function ToolFilters({
  search,
  onSearchChange,
  backend,
  onBackendChange,
  risk,
  onRiskChange,
  enabled,
  onEnabledChange,
  implemented,
  onImplementedChange,
}: ToolFiltersProps) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-ops-steel/10 bg-ops-cream p-4 xl:flex-row xl:items-end">
      <label className="min-w-0 flex-1 text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
        Search
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search name, display name, description..."
          className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-white px-4 py-2 text-sm normal-case tracking-normal text-ops-ink"
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <SelectField label="Backend" value={backend} onChange={onBackendChange} options={['all', 'pyvmomi', 'govc', 'vsphere_rest', 'mcp', 'internal', 'unknown']} />
        <SelectField label="Risk" value={risk} onChange={onRiskChange} options={['all', 'read_only', 'low_risk', 'approval_required', 'destructive']} />
        <SelectField label="Enabled" value={enabled} onChange={onEnabledChange} options={['all', 'enabled', 'disabled']} />
        <SelectField label="Implemented" value={implemented} onChange={onImplementedChange} options={['all', 'implemented', 'not implemented']} />
      </div>
    </div>
  )
}
