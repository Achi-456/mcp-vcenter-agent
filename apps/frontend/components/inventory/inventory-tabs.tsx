'use client'

import type { InventoryKind } from '@/lib/inventory-data'

const tabs: Array<{ key: InventoryKind; label: string }> = [
  { key: 'vms', label: 'Virtual Machines' },
  { key: 'hosts', label: 'Hosts' },
  { key: 'datastores', label: 'Datastores' },
]

export function InventoryTabs({ active, onChange }: { active: InventoryKind; onChange: (tab: InventoryKind) => void }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-2xl border border-ops-steel/10 bg-white p-2 shadow-card">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onChange(tab.key)}
          className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
            active === tab.key ? 'bg-ops-navy text-white' : 'text-ops-steel hover:bg-ops-cream'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
