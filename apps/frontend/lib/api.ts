import type { ApiEnvelope, ServiceHealthMap, ToolListResponse } from './types'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  DEFAULT_API_BASE_URL

export class ApiClientError extends Error {
  status: number
  errorCode?: string
  details?: Record<string, unknown>

  constructor(message: string, status: number, errorCode?: string, details?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.errorCode = errorCode
    this.details = details
  }
}

function joinUrl(path: string) {
  const base = API_BASE_URL.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

export function apiUrl(path: string) {
  return joinUrl(path)
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null

  try {
    return JSON.parse(text)
  } catch {
    throw new ApiClientError('API returned a non-JSON response.', response.status)
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  try {
    const response = await fetch(joinUrl(path), {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.headers ?? {}),
      },
      cache: 'no-store',
    })

    const payload = await parseJson(response)

    if (!response.ok) {
      const failure = payload as Partial<ApiEnvelope<T>>
      return {
        ok: false,
        error_code: 'HTTP_ERROR',
        message:
          'message' in failure && typeof failure.message === 'string'
            ? failure.message
            : `Request failed with HTTP ${response.status}.`,
        details: { status: response.status },
      }
    }

    if (
      payload &&
      typeof payload === 'object' &&
      'ok' in payload &&
      (payload as { ok?: unknown }).ok === false
    ) {
      return payload as ApiEnvelope<T>
    }

    if (
      payload &&
      typeof payload === 'object' &&
      'ok' in payload &&
      (payload as { ok?: unknown }).ok === true
    ) {
      return payload as ApiEnvelope<T>
    }

    return {
      ok: true,
      data: payload as T,
      metadata: { normalized: true },
    }
  } catch (error) {
    if (error instanceof ApiClientError) {
      return {
        ok: false,
        error_code: error.errorCode ?? 'API_CLIENT_ERROR',
        message: error.message,
        details: error.details ?? { status: error.status },
      }
    }

    return {
      ok: false,
      error_code: 'API_UNREACHABLE',
      message: error instanceof Error ? error.message : 'API request failed.',
      details: {},
    }
  }
}

export const api = {
  getHealthServices: () => apiGet<ServiceHealthMap>('/api/v1/health/services'),
  getTools: () => apiGet<ToolListResponse>('/api/v1/tools'),
}
