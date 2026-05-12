'use client'

import { useState } from 'react'

type RawToggleProps = {
  raw: string
  label?: string
}

export function RawToggle({ raw, label = 'View raw' }: RawToggleProps) {
  const [open, setOpen] = useState(false)

  async function copyRaw() {
    await navigator.clipboard.writeText(raw)
  }

  return (
    <div className="mt-3">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setOpen((current) => !current)}
          className="rounded-lg border border-ops-steel/15 bg-white px-3 py-1.5 text-xs font-semibold text-ops-steel hover:bg-ops-cream"
        >
          {open ? 'Hide raw' : label}
        </button>
        <button
          type="button"
          onClick={() => void copyRaw()}
          className="rounded-lg border border-ops-steel/15 bg-white px-3 py-1.5 text-xs font-semibold text-ops-steel hover:bg-ops-cream"
        >
          Copy raw
        </button>
      </div>
      {open ? (
        <pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">
          {raw}
        </pre>
      ) : null}
    </div>
  )
}
