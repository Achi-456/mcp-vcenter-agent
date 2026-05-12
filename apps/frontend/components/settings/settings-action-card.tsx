'use client'

type SettingsActionCardProps = {
  title: string
  description: string
  buttonLabel: string
  onAction: () => void | Promise<void>
  disabled?: boolean
  tone?: 'primary' | 'secondary'
}

export function SettingsActionCard({ title, description, buttonLabel, onAction, disabled = false, tone = 'primary' }: SettingsActionCardProps) {
  return (
    <article className="rounded-2xl border border-ops-steel/10 bg-ops-cream p-4">
      <h3 className="font-semibold text-ops-ink">{title}</h3>
      <p className="mt-1 text-sm leading-6 text-ops-muted">{description}</p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => void onAction()}
        className={`mt-4 rounded-xl px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-50 ${
          tone === 'primary' ? 'bg-ops-navy hover:bg-ops-steel' : 'bg-ops-steel hover:bg-ops-navy'
        }`}
      >
        {buttonLabel}
      </button>
    </article>
  )
}
