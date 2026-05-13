'use client'

import { useState } from 'react'
import type { ReactNode } from 'react'
import { RiskBadge, StatusBadge, ToolBadge } from '@/components/ui'
import type { ChatStreamEvent } from '@/lib/types'
import { MarkdownAnswer } from './markdown-answer'
import { RawToggle } from './raw-toggle'

function value(payload: Record<string, unknown>, key: string, fallback = '—') {
  const item = payload[key]
  if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') {
    return String(item)
  }
  return fallback
}

function CardShell({
  title,
  tone = 'default',
  children,
}: {
  title: string
  tone?: 'default' | 'info' | 'success' | 'warning' | 'danger'
  children: ReactNode
}) {
  const styles = {
    default: 'border-ops-steel/10 bg-white',
    info: 'border-ops-info bg-ops-info/20',
    success: 'border-emerald-200 bg-emerald-50',
    warning: 'border-amber-200 bg-amber-50',
    danger: 'border-red-200 bg-red-50',
  }

  return (
    <article className={`rounded-2xl border p-4 shadow-sm ${styles[tone]}`}>
      <h3 className="text-sm font-semibold text-ops-ink">{title}</h3>
      <div className="mt-3">{children}</div>
    </article>
  )
}

export function IntentCard({ event }: { event: ChatStreamEvent }) {
  return (
    <CardShell title="Intent" tone="info">
      <div className="grid gap-2 text-sm text-ops-muted md:grid-cols-2">
        <span>Task: {value(event.payload, 'task_type')}</span>
        <span>Object: {value(event.payload, 'object_type')}</span>
        <span>Entity: {value(event.payload, 'entity')}</span>
        <span>Tool: {value(event.payload, 'tool')}</span>
      </div>
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function SafetyCheckCard({ event }: { event: ChatStreamEvent }) {
  const allowed = event.payload.allowed !== false
  const message = value(event.payload, 'message', allowed ? 'Read-only request allowed.' : 'Blocked before tool call.')

  return (
    <CardShell title={allowed ? 'Safety Check' : 'Blocked Before Tool Call'} tone={allowed ? 'success' : 'danger'}>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={allowed ? 'allowed' : 'blocked'} />
        <RiskBadge risk={value(event.payload, 'risk_level', 'read_only')} />
      </div>
      <p className="mt-3 text-sm leading-6 text-ops-muted">{message}</p>
      {!allowed ? <p className="mt-2 text-sm font-semibold text-red-700">No action was taken.</p> : null}
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function AgentStartCard({ event }: { event: ChatStreamEvent }) {
  return (
    <CardShell title="Agent Started">
      <ToolBadge label={value(event.payload, 'agent', 'agent')} />
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function ToolCallCard({ event }: { event: ChatStreamEvent }) {
  return (
    <CardShell title="Tool Call" tone="info">
      <div className="flex flex-wrap items-center gap-2">
        <ToolBadge label={value(event.payload, 'tool', 'tool')} />
        <RiskBadge risk={value(event.payload, 'risk_level', 'read_only')} />
      </div>
      <p className="mt-3 text-sm text-ops-muted">{value(event.payload, 'input_summary', 'no arguments')}</p>
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function ToolResultCard({ event }: { event: ChatStreamEvent }) {
  const ok = event.payload.ok !== false
  const [collapsed, setCollapsed] = useState(true)

  return (
    <CardShell title="Tool Result" tone={ok ? 'success' : 'warning'}>
      <div className="flex flex-wrap items-center gap-2">
        <ToolBadge label={value(event.payload, 'tool', 'tool')} />
        <StatusBadge status={ok ? 'ok' : 'failed'} />
      </div>
      <p className="mt-3 text-sm leading-6 text-ops-muted">{value(event.payload, 'output_summary', 'result returned')}</p>
      <button
        type="button"
        onClick={() => setCollapsed((current) => !current)}
        className="mt-3 rounded-lg border border-ops-steel/15 bg-white px-3 py-1.5 text-xs font-semibold text-ops-steel hover:bg-ops-cream"
      >
        {collapsed ? 'Expand evidence' : 'Collapse evidence'}
      </button>
      {!collapsed ? <RawToggle raw={event.raw} label="View raw event" /> : null}
    </CardShell>
  )
}

export function ValidationCard({ event }: { event: ChatStreamEvent }) {
  return (
    <CardShell title="Validation" tone="success">
      <StatusBadge status={value(event.payload, 'status', 'passed')} />
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function FinalAnswerCard({ event }: { event: ChatStreamEvent }) {
  const content = value(event.payload, 'content', '')
  const answerSource = value(event.payload, 'final_answer_source', '')
  const answerSourceLabel = answerSource === 'llm' ? 'LLM answer' : answerSource === 'deterministic' ? 'Deterministic fallback' : ''

  async function copyAnswer() {
    await navigator.clipboard.writeText(content)
  }

  return (
    <CardShell title="Final Answer">
      {answerSourceLabel ? (
        <span className="mb-3 inline-flex rounded-full border border-ops-steel/15 bg-ops-cream px-3 py-1 text-xs font-semibold text-ops-steel">
          {answerSourceLabel}
        </span>
      ) : null}
      <MarkdownAnswer content={content} />
      {content.includes('No action was taken') ? (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
          No action was taken.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void copyAnswer()}
          className="rounded-lg bg-ops-navy px-3 py-1.5 text-xs font-semibold text-white hover:bg-ops-steel"
        >
          Copy answer
        </button>
        <RawToggle raw={event.raw} label="View raw answer event" />
      </div>
    </CardShell>
  )
}

export function ErrorCard({ event }: { event: ChatStreamEvent }) {
  return (
    <CardShell title="Stream Error" tone="warning">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status="error" />
        <ToolBadge label={value(event.payload, 'error_code', 'ERROR')} active={false} />
      </div>
      <p className="mt-3 text-sm leading-6 text-ops-muted">{value(event.payload, 'message', 'The stream returned an error.')}</p>
      <RawToggle raw={event.raw} />
    </CardShell>
  )
}

export function ChatEventCard({ event }: { event: ChatStreamEvent }) {
  if (event.type === 'intent') return <IntentCard event={event} />
  if (event.type === 'safety_check') return <SafetyCheckCard event={event} />
  if (event.type === 'agent_start') return <AgentStartCard event={event} />
  if (event.type === 'tool_call') return <ToolCallCard event={event} />
  if (event.type === 'tool_result') return <ToolResultCard event={event} />
  if (event.type === 'validation') return <ValidationCard event={event} />
  if (event.type === 'final') return <FinalAnswerCard event={event} />
  if (event.type === 'error') return <ErrorCard event={event} />
  if (event.type === 'start') {
    return (
      <CardShell title="Session Started">
        <p className="text-sm text-ops-muted">Run ID: {value(event.payload, 'run_id')}</p>
        <RawToggle raw={event.raw} />
      </CardShell>
    )
  }
  return null
}
