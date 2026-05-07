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
  getVMs: () => request<{ count: number; items: VM[] }>("/api/v1/inventory/vms"),
  getHosts: () => request<{ count: number; items: Host[] }>("/api/v1/inventory/hosts"),
  getDatastores: () => request<{ count: number; items: Datastore[] }>("/api/v1/inventory/datastores"),
  getClusters: () => request<{ count: number; items: Cluster[] }>("/api/v1/inventory/clusters"),

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

  // Tools
  getTools: () => request<{ tools: Tool[] }>("/api/v1/tools"),
}

export interface VM {
  name: string; moid: string; power_state: string; cpu: number; memory_mb: number
  guest_os: string | null; ip_address: string | null; host: string | null; template: boolean
}

export interface Host {
  name: string; moid: string; connection_state: string; power_state: string
  cpu_cores: number; cpu_mhz: number; memory_mb: number; num_vms: number
}

export interface Datastore {
  name: string; moid: string; type: string; capacity_gb: number; free_gb: number; url: string
}

export interface Cluster {
  name: string; moid: string; num_hosts: number; num_datastores: number
  total_cpu_mhz: number; total_memory_mb: number
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
