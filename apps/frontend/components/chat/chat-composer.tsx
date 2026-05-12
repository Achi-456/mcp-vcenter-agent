'use client'

import { FormEvent, useRef, useState } from 'react'

type ChatComposerProps = {
  disabled?: boolean
  onSend: (message: string) => void | Promise<void>
}

export function ChatComposer({ disabled = false, onSend }: ChatComposerProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  function resize() {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 168)}px`
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    void onSend(trimmed)
    setValue('')
    requestAnimationFrame(resize)
  }

  return (
    <form onSubmit={submit} className="rounded-2xl border border-ops-steel/10 bg-white p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-card">
      <label htmlFor="chat-input" className="sr-only">
        Ask AgenticOps
      </label>
      <textarea
        ref={textareaRef}
        id="chat-input"
        value={value}
        onChange={(event) => {
          setValue(event.target.value)
          requestAnimationFrame(resize)
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            event.currentTarget.form?.requestSubmit()
          }
        }}
        rows={2}
        placeholder="Ask about vCenter, diagnostics, safe MCP status, or tool results..."
        className="max-h-42 w-full resize-none rounded-xl border border-ops-steel/15 bg-ops-cream px-4 py-3 text-sm leading-6 text-ops-ink outline-none ring-ops-info/50 transition placeholder:text-ops-muted focus:ring-2"
        disabled={disabled}
      />
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-ops-muted">Enter to send, Shift+Enter for a new line.</p>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-xl bg-ops-navy px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-ops-steel disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabled ? 'Streaming...' : 'Send'}
        </button>
      </div>
    </form>
  )
}
