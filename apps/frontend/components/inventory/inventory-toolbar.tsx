'use client'

type InventoryToolbarProps = {
  search: string
  onSearchChange: (value: string) => void
  filters: Array<{
    label: string
    value: string
    options: Array<{ label: string; value: string }>
    onChange: (value: string) => void
  }>
  summary: string
}

export function InventoryToolbar({ search, onSearchChange, filters, summary }: InventoryToolbarProps) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-ops-steel/10 bg-ops-cream p-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0 flex-1">
        <label htmlFor="inventory-search" className="text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
          Search
        </label>
        <input
          id="inventory-search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search inventory..."
          className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-white px-4 py-2.5 text-sm text-ops-ink outline-none ring-ops-info/40 focus:ring-2"
        />
      </div>
      <div className="flex flex-wrap gap-3">
        {filters.map((filter) => (
          <label key={filter.label} className="text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
            {filter.label}
            <select
              value={filter.value}
              onChange={(event) => filter.onChange(event.target.value)}
              className="mt-2 block rounded-xl border border-ops-steel/15 bg-white px-3 py-2.5 text-sm normal-case tracking-normal text-ops-ink outline-none"
            >
              {filter.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <p className="text-sm font-semibold text-ops-steel">{summary}</p>
    </div>
  )
}
