'use client'

import { FormEvent, useState } from 'react'

type ChatMessage = {
  role: 'assistant' | 'user'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: "Hi, I'm your vCenter Agent. How can I help you with your infrastructure today?",
    },
  ])
  const [input, setInput] = useState('')

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return

    setMessages((current) => [
      ...current,
      { role: 'user', content: trimmed },
      {
        role: 'assistant',
        content:
          'Baseline chat is online. Next rebuild step is wiring this to the FastAPI SSE stream and agent engine.',
      },
    ])
    setInput('')
  }

  return (
    <main className="grid-shell min-h-screen px-6 py-8">
      <section className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1fr_320px]">
        <div className="rounded-3xl border border-emerald-400/20 bg-black/35 p-6 backdrop-blur">
          <div className="border-b border-emerald-400/15 pb-5">
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-300/80">
              Agent Console
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Chat</h1>
          </div>

          <div className="mt-6 flex min-h-[520px] flex-col gap-4">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'ml-auto bg-emerald-400 text-black'
                    : 'border border-emerald-400/15 bg-console-panel text-emerald-50'
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>

          <form onSubmit={submit} className="mt-6 flex gap-3">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about vCenter infrastructure..."
              className="min-w-0 flex-1 rounded-full border border-emerald-400/20 bg-black/40 px-5 py-3 text-sm text-white outline-none ring-emerald-300/40 transition placeholder:text-emerald-100/35 focus:ring-2"
            />
            <button
              type="submit"
              className="rounded-full bg-emerald-400 px-6 py-3 text-sm font-semibold text-black transition hover:bg-emerald-300"
            >
              Send
            </button>
          </form>
        </div>

        <aside className="rounded-3xl border border-emerald-400/20 bg-console-panel/80 p-6 backdrop-blur">
          <p className="text-xs uppercase tracking-[0.35em] text-emerald-300/80">
            Session Rail
          </p>
          <div className="mt-5 space-y-4 text-sm text-emerald-50/70">
            <p>Current branch is a rebuild baseline.</p>
            <p>SSE event rendering comes after backend and engine contracts stabilize.</p>
            <p>No vCenter credentials or API keys are stored in this UI.</p>
          </div>
        </aside>
      </section>
    </main>
  )
}

