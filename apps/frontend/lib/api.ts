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

export async function apiGet<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<ApiEnvelope<T>> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), init?.timeoutMs ?? 12000)

  try {
    const response = await fetch(joinUrl(path), {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.headers ?? {}),
      },
      cache: 'no-store',
      signal: init?.signal ?? controller.signal,
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
      error_code: error instanceof DOMException && error.name === 'AbortError' ? 'API_TIMEOUT' : 'API_UNREACHABLE',
      message:
        error instanceof DOMException && error.name === 'AbortError'
          ? 'API request timed out.'
          : error instanceof Error
            ? error.message
            : 'API request failed.',
      details: {},
    }
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  getHealthServices: () => apiGet<ServiceHealthMap>('/api/v1/health/services'),
  getEnvironment: () => apiGet<unknown>('/api/v1/context/environment'),
  getVms: () => apiGet<unknown>('/api/v1/inventory/vms'),
  getHosts: () => apiGet<unknown>('/api/v1/inventory/hosts'),
  getDatastores: () => apiGet<unknown>('/api/v1/inventory/datastores'),
  getDatastoreHealth: () => apiGet<unknown>('/api/v1/context/datastore-health'),
  getVmDetails: (name: string) => apiGet<unknown>(`/api/v1/context/vm-details?name=${encodeURIComponent(name)}`),
  getHostDetails: (name: string) => apiGet<unknown>(`/api/v1/context/host-details?name=${encodeURIComponent(name)}`),
  getAlarms: () => apiGet<unknown>('/api/v1/monitoring/alarms'),
  getEvents: () => apiGet<unknown>('/api/v1/monitoring/events?limit=50'),
  getRke2Vms: () => apiGet<unknown>('/api/v1/context/rke2-vms'),
  getGovcAbout: () => apiGet<unknown>('/api/v1/govc/about'),
  getGovcVmInfo: (name: string) => apiGet<unknown>(`/api/v1/govc/vm-info?name=${encodeURIComponent(name)}`),
  getGovcHostInfo: (name: string) => apiGet<unknown>(`/api/v1/govc/host-info?name=${encodeURIComponent(name)}`),
  getGovcDatastoreInfo: () => apiGet<unknown>('/api/v1/govc/datastore-info'),
  getGovcEvents: () => apiGet<unknown>('/api/v1/govc/events'),
  getGovcVolumeLs: () => apiGet<unknown>('/api/v1/govc/volume-ls'),
  getVsphereRestAbout: () => apiGet<unknown>('/api/v1/vsphere-rest/about'),
  getVsphereRestApplianceHealth: () => apiGet<unknown>('/api/v1/vsphere-rest/appliance/health'),
  getVsphereRestTagCategories: () => apiGet<unknown>('/api/v1/vsphere-rest/tag-categories'),
  getVsphereRestTags: () => apiGet<unknown>('/api/v1/vsphere-rest/tags'),
  getVsphereRestAttachedTags: (objectId: string) => apiGet<unknown>(`/api/v1/vsphere-rest/tags/attached?object_id=${encodeURIComponent(objectId)}`),
  getVsphereRestContentLibraries: () => apiGet<unknown>('/api/v1/vsphere-rest/content-libraries'),
  getVsphereRestLibraryItems: (libraryId: string) => apiGet<unknown>(`/api/v1/vsphere-rest/content-libraries/${encodeURIComponent(libraryId)}/items`),
  getVsphereRestRecentTasks: () => apiGet<unknown>('/api/v1/vsphere-rest/tasks/recent'),
  getVcenterStatus: () => apiGet<unknown>('/api/v1/connections/vcenter/status'),
  getMcpDefaultStatus: () => apiGet<unknown>('/api/v1/mcp/servers/default/status'),
  getMcpTools: () => apiGet<unknown>('/api/v1/mcp/tools'),
  getTools: () => apiGet<ToolListResponse>('/api/v1/tools'),
}
