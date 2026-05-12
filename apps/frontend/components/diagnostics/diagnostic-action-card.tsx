'use client'

type DiagnosticActionCardProps = {
  title: string
  description: string
  inputLabel?: string
  inputValue?: string
  inputPlaceholder?: string
  onInputChange?: (value: string) => void
  onRun: () => void | Promise<void>
  disabled?: boolean
}

export function DiagnosticActionCard({
  title,
  description,
  inputLabel,
  inputValue,
  inputPlaceholder,
  onInputChange,
  onRun,
  disabled = false,
}: DiagnosticActionCardProps) {
  return (
    <article className="rounded-2xl border border-ops-steel/10 bg-white p-4 shadow-sm">
      <h3 className="font-semibold text-ops-ink">{title}</h3>
      <p className="mt-1 text-sm leading-6 text-ops-muted">{description}</p>
      {inputLabel ? (
        <label className="mt-4 block text-xs font-bold uppercase tracking-[0.18em] text-ops-muted">
          {inputLabel}
          <input
            value={inputValue ?? ''}
            onChange={(event) => onInputChange?.(event.target.value)}
            placeholder={inputPlaceholder}
            className="mt-2 w-full rounded-xl border border-ops-steel/15 bg-ops-cream px-3 py-2 text-sm normal-case tracking-normal text-ops-ink outline-none"
          />
        </label>
      ) : null}
      <button
        type="button"
        disabled={disabled}
        onClick={() => void onRun()}
        className="mt-4 rounded-xl bg-ops-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-ops-steel disabled:cursor-not-allowed disabled:opacity-50"
      >
        Run
      </button>
    </article>
  )
}
