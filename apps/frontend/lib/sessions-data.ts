import { arrayFrom, objectFrom, stringValue } from './dashboard-data'
import { redactSensitive } from './settings-data'

export type NormalizedSession = {
  id: string
  createdAt: string
  updatedAt: string
  prompt: string
  status: string
  count: string
  raw: unknown
}

export type NormalizedActivity = {
  id: string
  timestamp: string
  action: string
  status: string
  summary: string
  actor: string
  raw: unknown
}

export function normalizeSessions(payload: unknown): NormalizedSession[] {
  return arrayFrom(payload).map((session, index) => ({
    id: stringValue(session, ['session_id', 'id', 'run_id'], `session-${index + 1}`),
    createdAt: stringValue(session, ['created_at', 'createdAt', 'timestamp'], '—'),
    updatedAt: stringValue(session, ['updated_at', 'updatedAt', 'last_updated'], '—'),
    prompt: stringValue(session, ['last_message_preview', 'title', 'last_prompt', 'prompt', 'objective', 'message'], '—'),
    status: stringValue(session, ['status', 'state'], 'unknown'),
    count: stringValue(session, ['message_count', 'tool_count', 'run_count', 'tools', 'runs'], '—'),
    raw: redactSensitive(session),
  }))
}

export function normalizeActivities(payload: unknown): NormalizedActivity[] {
  return arrayFrom(payload).map((event, index) => ({
    id: stringValue(event, ['id', 'event_id'], `event-${index + 1}`),
    timestamp: stringValue(event, ['timestamp', 'created_at', 'time'], '—'),
    action: stringValue(event, ['event_type', 'action', 'tool_name', 'tool'], '—'),
    status: stringValue(event, ['status', 'outcome'], 'unknown'),
    summary: stringValue(event, ['summary', 'message', 'description'], '—'),
    actor: stringValue(event, ['actor', 'user', 'source'], '—'),
    raw: redactSensitive(objectFrom(event)),
  }))
}
