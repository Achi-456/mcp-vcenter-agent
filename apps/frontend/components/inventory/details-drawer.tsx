'use client'

import { useCallback } from 'react'
import { api } from '@/lib/api'
import { formatGb, formatPercent, objectEntries, type InventoryRow } from '@/lib/inventory-data'
import { ErrorState, LoadingState, StatusBadge } from '@/components/ui'
import { RawToggle } from '@/components/chat'
import { useApiResource } from '@/hooks/use-api-resource'

function DetailRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-ops-steel/10 py-2 text-sm">
      <span className="font-semibold text-ops-muted">{label}</span>
      <span className="text-right text-ops-ink">{value ?? '—'}</span>
    </div>
  )
}

function promptFor(row: InventoryRow) {
  if (row.kind === 'vms') return `check ${row.name}`
  if (row.kind === 'hosts') return `get host details for ${row.name}`
  return `show datastore health for ${row.name}`
}

export function DetailsDrawer({ row, onClose }: { row: InventoryRow | null; onClose: () => void }) {
  const detailLoader = useCallback(() => {
    if (!row) return Promise.resolve({ ok: true as const, data: null })
    if (row.kind === 'vms') return api.getVmDetails(row.name)
    if (row.kind === 'hosts') return api.getHostDetails(row.name)
    return Promise.resolve({ ok: true as const, data: row.raw })
  }, [row])

  const details = useApiResource(detailLoader)

  if (!row) return null
  const prompt = promptFor(row)

  return (
    <div className="fixed inset-0 z-40 bg-slate-950/30">
      <aside className="ml-auto flex h-full w-full max-w-xl flex-col overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-ops-steel">Inventory Details</p>
            <h2 className="mt-2 text-2xl font-bold text-ops-ink">{row.name}</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl border border-ops-steel/15 px-3 py-2 text-sm font-semibold text-ops-steel">
            Close
          </button>
        </div>

        <div className="mt-5 rounded-2xl bg-ops-cream p-4">
          <p className="text-sm font-semibold text-ops-ink">Suggested AI prompt</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <code className="rounded-lg bg-white px-3 py-2 font-mono text-xs text-ops-navy">{prompt}</code>
            <button
              type="button"
              onClick={() => void navigator.clipboard.writeText(prompt)}
              className="rounded-lg bg-ops-navy px-3 py-2 text-xs font-semibold text-white"
            >
              Copy
            </button>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-ops-steel/10 p-4">
          {row.kind === 'vms' ? (
            <>
              <DetailRow label="Power State" value={row.powerState} />
              <DetailRow label="CPU" value={row.cpu} />
              <DetailRow label="Memory" value={formatGb(row.memoryGb)} />
              <DetailRow label="Guest OS" value={row.guestOs} />
              <DetailRow label="IP Address" value={row.ipAddress} />
              <DetailRow label="Host" value={row.host} />
              <DetailRow label="Datastore" value={row.datastore} />
              <DetailRow label="VMware Tools" value={row.toolsStatus} />
            </>
          ) : null}
          {row.kind === 'hosts' ? (
            <>
              <DetailRow label="Connection State" value={row.connectionState} />
              <DetailRow label="Power State" value={row.powerState} />
              <DetailRow label="Version" value={row.version} />
              <DetailRow label="Build" value={row.build} />
              <DetailRow label="Vendor" value={row.vendor} />
              <DetailRow label="Model" value={row.model} />
              <DetailRow label="CPU Cores" value={row.cpuCores} />
              <DetailRow label="Memory" value={formatGb(row.memoryGb)} />
              <DetailRow label="VM Count" value={row.vmCount} />
            </>
          ) : null}
          {row.kind === 'datastores' ? (
            <>
              <DetailRow label="Type" value={row.type} />
              <DetailRow label="Capacity" value={formatGb(row.capacityGb)} />
              <DetailRow label="Free" value={formatGb(row.freeGb)} />
              <DetailRow label="Used" value={formatPercent(row.usedPercent)} />
              <div className="flex items-center justify-between gap-4 border-b border-ops-steel/10 py-2 text-sm">
                <span className="font-semibold text-ops-muted">Health</span>
                <StatusBadge status={row.health} />
              </div>
              <DetailRow label="Accessible" value={row.accessible} />
              <DetailRow label="Message" value={row.message || '—'} />
            </>
          ) : null}
        </div>

        <div className="mt-5 rounded-2xl border border-ops-steel/10 p-4">
          <h3 className="font-semibold text-ops-ink">Backend detail response</h3>
          {details.isLoading ? <LoadingState label="Loading details..." /> : null}
          {details.error ? <ErrorState message={details.error} code={details.errorCode} /> : null}
          {details.data ? (
            <div className="mt-3 space-y-2">
              {objectEntries(details.data)
                .slice(0, 8)
                .map(([key, value]) => (
                  <DetailRow key={key} label={key} value={String(value)} />
                ))}
              <RawToggle raw={JSON.stringify(details.data, null, 2)} />
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  )
}
