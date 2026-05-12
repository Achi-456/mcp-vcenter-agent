import type { ApiEnvelope } from './types'

export type ResourceLike<T> = {
  data: T | null
  error: string | null
  lastUpdated: Date | null
  isRefreshing: boolean
  refresh: () => Promise<void>
}

export function unwrapData(value: unknown): unknown {
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    if ('data' in record) return record.data
  }
  return value
}

export function arrayFrom(value: unknown): unknown[] {
  const data = unwrapData(value)
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>
    for (const key of ['items', 'results', 'vms', 'hosts', 'datastores', 'alarms', 'events', 'tools']) {
      if (Array.isArray(record[key])) return record[key] as unknown[]
    }
  }
  return []
}

export function objectFrom(value: unknown): Record<string, unknown> {
  const data = unwrapData(value)
  return data && typeof data === 'object' && !Array.isArray(data) ? (data as Record<string, unknown>) : {}
}

export function stringValue(value: unknown, keys: string[], fallback = '—') {
  const record = objectFrom(value)
  for (const key of keys) {
    const item = record[key]
    if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') return String(item)
  }
  return fallback
}

export function numberValue(value: unknown, keys: string[], fallback = 0) {
  const record = objectFrom(value)
  for (const key of keys) {
    const item = record[key]
    if (typeof item === 'number') return item
    if (typeof item === 'string' && item.trim() && !Number.isNaN(Number(item))) return Number(item)
  }
  return fallback
}

export function statusValue(value: unknown, fallback = 'unknown') {
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? 'online' : 'offline'
  const record = objectFrom(value)
  for (const key of ['status', 'state', 'health', 'connection_state', 'configured']) {
    const item = record[key]
    if (typeof item === 'string') return item
    if (typeof item === 'boolean') return item ? 'online' : 'offline'
  }
  return fallback
}

export function successful<T>(result: ApiEnvelope<T>) {
  return result.ok ? result.data : null
}

export function formatDate(value: Date | null) {
  if (!value) return 'Not checked yet'
  return value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function firstUpdated(resources: Array<{ lastUpdated: Date | null }>) {
  const dates = resources.map((resource) => resource.lastUpdated).filter((date): date is Date => Boolean(date))
  if (!dates.length) return null
  return new Date(Math.max(...dates.map((date) => date.getTime())))
}

export function hasFailures(resources: Array<{ error: string | null }>) {
  return resources.some((resource) => Boolean(resource.error))
}

export function isRefreshing(resources: Array<{ isRefreshing: boolean }>) {
  return resources.some((resource) => resource.isRefreshing)
}

export async function refreshAll(resources: Array<{ refresh: () => Promise<void> }>) {
  await Promise.allSettled(resources.map((resource) => resource.refresh()))
}
