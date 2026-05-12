'use client'

const suggestions = [
  'check roshellevm02',
  'summarize vCenter health',
  'critical datastores?',
  'show active alarms',
  'compare pyVmomi and govc for roshellevm02',
  'verify roshellevm02 with govc',
  'show vSphere tags',
  'test MCP',
]

export function PromptSuggestions({ onSelect }: { onSelect: (prompt: string) => void | Promise<void> }) {
  return (
    <div className="grid gap-2">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => void onSelect(suggestion)}
          className="rounded-xl bg-white px-3 py-2 text-left font-mono text-xs text-ops-ink ring-1 ring-ops-steel/10 transition hover:bg-ops-cream hover:ring-ops-steel/25"
        >
          {suggestion}
        </button>
      ))}
    </div>
  )
}
