import type { ChatMessage, ChatStreamEvent } from '@/lib/types'
import { StatusBadge } from '@/components/ui'
import { ExecutionDetails } from './execution-details'
import { LiveProgress } from './live-progress'
import { MarkdownAnswer } from './markdown-answer'
import { ToolSummaryChips } from './tool-summary-chips'

function value(payload: Record<string, unknown>, key: string, fallback = '') {
  const item = payload[key]
  if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') return String(item)
  return fallback
}

function finalAnswer(events: ChatStreamEvent[]) {
  const finalEvent = [...events].reverse().find((event) => event.type === 'final')
  const content = finalEvent ? value(finalEvent.payload, 'content') : ''
  return content.replace(/(No action was taken\.\s*){2,}/gi, 'No action was taken.')
}

function finalSource(events: ChatStreamEvent[]) {
  const finalEvent = [...events].reverse().find((event) => event.type === 'final')
  const source = finalEvent ? value(finalEvent.payload, 'final_answer_source', '') : ''
  if (source === 'llm') return 'LLM answer'
  if (source === 'deterministic') return 'Deterministic fallback'
  return ''
}

function blockedAnswer(events: ChatStreamEvent[]) {
  const safety = events.find((event) => event.type === 'safety_check' && event.payload.allowed === false)
  if (!safety) return ''
  const reason = value(safety.payload, 'message', 'This request was blocked by the safety policy.')
  return `This request was blocked before any tool call.\n\nReason: ${reason}\n\nNo action was taken.`
}

function errorAnswer(events: ChatStreamEvent[]) {
  const error = events.find((event) => event.type === 'error')
  if (!error) return ''
  return value(error.payload, 'message', 'The assistant encountered an error while streaming the response.')
}

async function copyAnswer(content: string) {
  await navigator.clipboard.writeText(content)
}

export function AssistantAnswer({ message }: { message: ChatMessage }) {
  const events = message.events ?? []
  const hasDone = events.some((event) => event.type === 'done')
  const blocked = events.some((event) => event.type === 'safety_check' && event.payload.allowed === false)
  const content = finalAnswer(events) || blockedAnswer(events) || errorAnswer(events)
  const answerSource = finalSource(events)
  const answerTone = blocked ? 'border-red-200 bg-red-50' : 'border-ops-steel/10 bg-white'

  return (
    <div className={`rounded-3xl border p-5 shadow-card ${answerTone}`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ops-ink">AgenticOps Assistant</p>
          <p className="mt-1 text-xs text-ops-muted">Final answer first. Execution trace is collapsed below.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {answerSource ? <span className="rounded-full border border-ops-steel/15 bg-ops-cream px-3 py-1 text-xs font-semibold text-ops-steel">{answerSource}</span> : null}
          <StatusBadge status={blocked ? 'blocked' : hasDone ? 'complete' : 'streaming'} />
        </div>
      </div>

      {!content ? <LiveProgress events={events} /> : null}

      {content ? (
        <div className="rounded-2xl bg-white/80 p-4">
          <MarkdownAnswer content={content} />
          <button
            type="button"
            onClick={() => void copyAnswer(content)}
            className="mt-4 rounded-lg bg-ops-navy px-3 py-1.5 text-xs font-semibold text-white hover:bg-ops-steel"
          >
            Copy answer
          </button>
        </div>
      ) : null}

      <ToolSummaryChips events={events} />
      <ExecutionDetails events={events} />
    </div>
  )
}
