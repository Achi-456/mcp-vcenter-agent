import type { ChatMessage } from '@/lib/types'
import { ChatEventCard } from './event-cards'

export function ChatMessageList({ messages }: { messages: ChatMessage[] }) {
  if (!messages.length) {
    return (
      <div className="rounded-2xl border border-dashed border-ops-steel/25 bg-white/75 p-8 text-center">
        <h2 className="text-lg font-semibold text-ops-ink">Start an investigation</h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-ops-muted">
          Ask a read-only question. The assistant will show intent, safety, tool calls, validation, and the final answer as separate operation cards.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {messages.map((message) => {
        if (message.role === 'user') {
          return (
            <div key={message.id} className="flex justify-end">
              <div className="max-w-2xl rounded-2xl bg-ops-navy px-5 py-3 text-sm leading-6 text-white shadow-sm">
                {message.content}
              </div>
            </div>
          )
        }

        return (
          <div key={message.id} className="space-y-3">
            {(message.events ?? []).map((event) => (
              <ChatEventCard key={event.id} event={event} />
            ))}
            {!message.events?.length ? (
              <div className="rounded-2xl border border-ops-steel/10 bg-white p-4 text-sm text-ops-muted shadow-sm">
                Waiting for Agent Engine events...
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
