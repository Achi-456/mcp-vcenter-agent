'use client'

import { useState } from 'react'
import { ErrorState, StatusBadge } from '@/components/ui'
import { RawToggle } from '@/components/chat'
import { extractArrayItems, extractObjectFields, formatJsonSummary } from '@/lib/diagnostics-data'
import { redactSensitive } from '@/lib/settings-data'
import type { ApiEnvelope } from '@/lib/types'

type DiagnosticResultPanelProps = {
  title: string
  result: ApiEnvelope<unknown> | null
  isLoading?: boolean
}

export function DiagnosticResultPanel({ title, result, isLoading = false }: DiagnosticResultPanelProps) {
  const [copied, setCopied] = useState(false)

  async function copyResult() {
    await navigator.clipboard.writeText(JSON.stringify(redactSensitive(result), null, 2))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  if (!result && !isLoading) {
    return (
      <div className="rounded-2xl border border-dashed border-ops-steel/20 bg-white/70 p-6 text-sm text-ops-muted">
        Run a diagnostic action to see summarized results here.
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-ops-info bg-ops-info/20 p-5 text-sm font-semibold text-ops-navy">
        Running diagnostic...
      </div>
    )
  }

  if (!result) return null

  if (!result.ok) {
    const providerLimited =
      result.error_code?.toLowerCase().includes('unsupported') || result.message.toLowerCase().includes('unsupported')
    return (
      <div className="space-y-3">
        <ErrorState
          title={providerLimited ? 'Provider-limited response' : 'Diagnostic failed'}
          message={providerLimited ? 'This vCenter REST provider does not expose this operation. No fake success data is shown.' : result.message}
          code={result.error_code}
        />
        <RawToggle raw={JSON.stringify(redactSensitive(result), null, 2)} />
      </div>
    )
  }

  const items = extractArrayItems(result.data)
  const fields = extractObjectFields(result.data)

  return (
    <section className="space-y-4 rounded-2xl border border-ops-steel/10 bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-ops-ink">{title}</h3>
          <p className="mt-1 text-sm text-ops-muted">{formatJsonSummary(result.data)}</p>
        </div>
        <StatusBadge status="ok" />
      </div>

      {items.length ? (
        <div className="overflow-x-auto rounded-xl border border-ops-steel/10">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead className="bg-ops-cream">
              <tr>
                {Object.keys((items[0] as Record<string, unknown>) ?? {})
                  .slice(0, 6)
                  .map((key) => (
                    <th key={key} className="border-b border-ops-steel/10 px-3 py-2 font-semibold text-ops-ink">
                      {key}
                    </th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 10).map((item, index) => {
                const record = item && typeof item === 'object' ? (item as Record<string, unknown>) : {}
                return (
                  <tr key={index}>
                    {Object.keys(record)
                      .slice(0, 6)
                      .map((key) => (
                        <td key={`${index}-${key}`} className="border-b border-ops-steel/10 px-3 py-2 text-ops-muted">
                          {String(record[key] ?? '—')}
                        </td>
                      ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {!items.length && fields.length ? (
        <div className="grid gap-2 md:grid-cols-2">
          {fields.slice(0, 12).map(([key, value]) => (
            <div key={key} className="rounded-xl bg-ops-cream px-3 py-2 text-sm">
              <span className="font-semibold text-ops-muted">{key}: </span>
              <span className="text-ops-ink">{String(value ?? '—')}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => void copyResult()} className="rounded-lg bg-ops-navy px-3 py-1.5 text-xs font-semibold text-white">
          {copied ? 'Copied' : 'Copy result'}
        </button>
      </div>
      <RawToggle raw={JSON.stringify(redactSensitive(result), null, 2)} />
    </section>
  )
}
