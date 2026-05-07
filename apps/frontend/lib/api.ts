const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.dclab.local"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body.slice(0, 120)}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  // Health
  health: () => request<{ status: string }>("/health"),

  // Chat
  chatUrl: () => `${BASE_URL}/api/v1/chat`,

  // Inventory
  getInventoryOverview: () => request<InventoryOverview>("/api/v1/inventory/overview"),
  getVMs: (refresh?: boolean) => request<InventoryList<VM>>("/api/v1/inventory/vms" + (refresh ? "?refresh=true" : "")),
  getHosts: (refresh?: boolean) => request<InventoryList<Host>>("/api/v1/inventory/hosts" + (refresh ? "?refresh=true" : "")),
  getDatastores: (refresh?: boolean) => request<InventoryList<Datastore>>("/api/v1/inventory/datastores" + (refresh ? "?refresh=true" : "")),
  getNetworks: () => request<InventoryList<NetworkItem>>("/api/v1/inventory/networks"),
  getClusters: () => request<InventoryList<Cluster>>("/api/v1/inventory/clusters"),

  // Sessions
  getSessions: () => request<{ items: Session[] }>("/api/v1/sessions"),
  getSession: (id: string) => request<Session>("/api/v1/sessions/" + id),

  // Settings
  getSettings: () => request<SettingsItems>("/api/v1/settings"),
  updateSetting: (key: string, value: string) =>
    request<{ key: string; value: string }>("/api/v1/settings/" + key, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  testVcenter: () => request<{ status: string; message: string }>("/api/v1/settings/test/vcenter", { method: "POST" }),
  testLLM: () => request<{ status: string; message: string }>("/api/v1/settings/test/llm", { method: "POST" }),
  getSettingsStatus: () => request<{ vcenter: { status: string }; llm: { status: string; provider: string } }>("/api/v1/settings/status"),

  // Connections (Phase 1.2)
  testVCenterConnection: (payload: VCenterConnectionPayload) =>
    request<VCenterTestResponse>("/api/v1/connections/vcenter/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveVCenterConnection: (payload: VCenterConnectionPayload) =>
    request<VCenterSaveResponse>("/api/v1/connections/vcenter", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getVCenterConnectionStatus: () =>
    request<VCenterConnectionStatus>("/api/v1/connections/vcenter/status"),
  deleteVCenterConnection: () =>
    request<ConnectionDeleteResponse>("/api/v1/connections/vcenter", { method: "DELETE" }),
  testLLMConnection: (payload: LLMConnectionPayload) =>
    request<LLMTestResponse>("/api/v1/connections/llm/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveLLMConnection: (payload: LLMConnectionPayload) =>
    request<LLMSaveResponse>("/api/v1/connections/llm", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getLLMConnectionStatus: () =>
    request<LLMConnectionStatus>("/api/v1/connections/llm/status"),
  deleteLLMConnection: () =>
    request<ConnectionDeleteResponse>("/api/v1/connections/llm", { method: "DELETE" }),

  // Tools
  getTools: () => request<{ tools: Tool[] }>("/api/v1/tools"),
}

export interface VCenterConnectionPayload {
  name: string; vcenter_url: string; username: string; password: string; verify_ssl: boolean
}
export interface VCenterTestResponse { ok: boolean; status: string; message: string; error_code: string | null }
export interface VCenterConnectionStatus {
  configured: boolean; name: string | null; vcenter_url: string | null
  username_hint: string | null; verify_ssl: boolean | null; password_set: boolean
  last_test_status: string | null; last_tested_at: string | null
}
export interface VCenterSaveResponse { ok: boolean; status: string; message: string; connection: VCenterConnectionStatus | null }
export interface LLMConnectionPayload { provider: string; base_url: string; model: string; api_key: string }
export interface LLMTestResponse { ok: boolean; status: string; message: string; error_code: string | null }
export interface LLMConnectionStatus {
  configured: boolean; provider: string | null; base_url: string | null
  model: string | null; api_key_set: boolean; last_test_status: string | null; last_tested_at: string | null
}
export interface LLMSaveResponse { ok: boolean; status: string; message: string; connection: LLMConnectionStatus | null }
export interface ConnectionDeleteResponse { ok: boolean; status: string; message: string }

export interface VM {
  id: string; name: string; power_state: string; cpu: number; memory_gb: number
  guest_os: string | null; ip_address: string | null; host: string | null
  cluster: string | null; datastore: string | null; tools_status: string | null
  uptime_seconds: number | null; path: string | null
}

export interface Host {
  id: string; name: string; connection_state: string; power_state: string
  cpu_cores: number; cpu_threads: number; memory_gb: number; vm_count: number
  vendor: string | null; model: string | null; version: string | null; cluster: string | null
}

export interface Datastore {
  id: string; name: string; type: string; capacity_gb: number; free_gb: number
  used_gb: number; used_percent: number; accessible: boolean; multiple_host_access: boolean
}

export interface NetworkItem {
  id: string; name: string; type: string; accessible: boolean
}

export interface Cluster {
  id: string; name: string; num_hosts: number; num_vms: number
  total_cpu_mhz: number; total_memory_mb: number
}

export interface InventoryList<T> {
  items: T[]; count: number; source: string; cached: boolean; collected_at: string
}

export interface InventoryOverview {
  vms: { total: number; powered_on: number; powered_off: number; suspended: number }
  hosts: { total: number; connected: number; maintenance: number; disconnected: number }
  datastores: { total: number; capacity_gb: number; free_gb: number; used_percent: number }
  networks: { total: number }
  source: string; cached: boolean; collected_at: string
}

export interface Session {
  id: string; title: string; created_at: string; updated_at: string; message_count: number
}

export interface Tool {
  name: string; version: string; risk_level: string; read_only: boolean
}

export interface Setting {
  key: string; value: string; category: string; label: string; sensitive: boolean
}

export interface SettingsItems {
  items: Setting[]
}
