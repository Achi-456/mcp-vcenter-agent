'use client'

import { EmptyState, StatusBadge } from '@/components/ui'

export type SortDirection = 'asc' | 'desc'

export type Column<Row> = {
  key: string
  label: string
  sortable?: boolean
  render: (row: Row) => React.ReactNode
}

type InventoryTableProps<Row> = {
  rows: Row[]
  columns: Array<Column<Row>>
  sortKey: string
  sortDirection: SortDirection
  onSort: (key: string) => void
  onRowClick: (row: Row) => void
  emptyTitle: string
}

export function ProgressBar({ value }: { value: number | null }) {
  if (value === null) return <span>—</span>
  const tone = value >= 90 ? 'bg-red-500' : value >= 75 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="min-w-36">
      <div className="mb-1 text-xs font-semibold text-ops-ink">{value.toFixed(1)}%</div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  )
}

export function InventoryTable<Row extends { name: string }>({
  rows,
  columns,
  sortKey,
  sortDirection,
  onSort,
  onRowClick,
  emptyTitle,
}: InventoryTableProps<Row>) {
  if (!rows.length) {
    return <EmptyState title={emptyTitle} description="Adjust search or filters, or refresh inventory data." />
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-ops-steel/10">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="sticky top-0 bg-ops-cream">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="border-b border-ops-steel/10 px-3 py-3 font-semibold text-ops-ink">
                {column.sortable ? (
                  <button type="button" onClick={() => onSort(column.key)} className="inline-flex items-center gap-1 hover:text-ops-steel">
                    {column.label}
                    {sortKey === column.key ? <span>{sortDirection === 'asc' ? '↑' : '↓'}</span> : null}
                  </button>
                ) : (
                  column.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} onClick={() => onRowClick(row)} className="cursor-pointer transition hover:bg-ops-cream/70">
              {columns.map((column) => (
                <td key={`${row.name}-${column.key}`} className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function InventoryStatus({ status }: { status: string }) {
  return <StatusBadge status={status} />
}
