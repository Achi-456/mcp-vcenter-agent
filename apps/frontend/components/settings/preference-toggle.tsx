'use client'

type PreferenceToggleProps = {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

export function PreferenceToggle({ label, description, checked, onChange }: PreferenceToggleProps) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-ops-steel/10 bg-white p-4">
      <span>
        <span className="block font-semibold text-ops-ink">{label}</span>
        <span className="mt-1 block text-sm leading-6 text-ops-muted">{description}</span>
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 h-5 w-5 accent-ops-navy" />
    </label>
  )
}
