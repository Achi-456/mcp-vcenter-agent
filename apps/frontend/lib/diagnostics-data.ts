import { arrayFrom, objectFrom, stringValue } from './dashboard-data'

export function extractArrayItems(payload: unknown) {
  return arrayFrom(payload)
}

export function extractObjectFields(payload: unknown) {
  return Object.entries(objectFrom(payload)).filter(([, value]) => typeof value !== 'object' || value === null)
}

export function formatJsonSummary(payload: unknown) {
  const items = extractArrayItems(payload)
  if (items.length) return `${items.length} item(s) returned`
  const fields = extractObjectFields(payload)
  if (fields.length) return `${fields.length} field(s) returned`
  if (payload === null || payload === undefined) return 'No data returned'
  return 'Result returned'
}

export function safeText(value: unknown, keys: string[], fallback = '—') {
  return stringValue(value, keys, fallback)
}

export function compareFields(left: unknown, right: unknown, fields: Array<{ label: string; leftKeys: string[]; rightKeys: string[] }>) {
  return fields.map((field) => {
    const leftValue = safeText(left, field.leftKeys)
    const rightValue = safeText(right, field.rightKeys)
    const unavailable = leftValue === '—' || rightValue === '—'
    return {
      field: field.label,
      pyvmomi: leftValue,
      govc: rightValue,
      status: unavailable ? 'unavailable' : leftValue.toLowerCase() === rightValue.toLowerCase() ? 'matched' : 'mismatched',
    }
  })
}
