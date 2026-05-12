import { arrayFrom, numberValue, objectFrom, statusValue, stringValue } from './dashboard-data'

export type InventoryKind = 'vms' | 'hosts' | 'datastores'

export type NormalizedVm = {
  kind: 'vms'
  name: string
  powerState: string
  cpu: number | null
  memoryGb: number | null
  guestOs: string
  ipAddress: string
  host: string
  datastore: string
  toolsStatus: string
  raw: unknown
}

export type NormalizedHost = {
  kind: 'hosts'
  name: string
  connectionState: string
  powerState: string
  version: string
  build: string
  vendor: string
  model: string
  cpuCores: number | null
  memoryGb: number | null
  vmCount: number | null
  raw: unknown
}

export type NormalizedDatastore = {
  kind: 'datastores'
  name: string
  type: string
  capacityGb: number | null
  freeGb: number | null
  usedPercent: number | null
  health: string
  accessible: string
  message: string
  raw: unknown
}

export type InventoryRow = NormalizedVm | NormalizedHost | NormalizedDatastore

export function safeText(value: unknown, keys: string[], fallback = '—') {
  return stringValue(value, keys, fallback)
}

export function safeNumber(value: unknown, keys: string[]) {
  const result = numberValue(value, keys, Number.NaN)
  return Number.isNaN(result) ? null : result
}

export function formatGb(value: number | null) {
  if (value === null) return '—'
  return value >= 1024 ? `${(value / 1024).toFixed(1)} TB` : `${value.toFixed(1)} GB`
}

export function formatPercent(value: number | null) {
  return value === null ? '—' : `${value.toFixed(1)}%`
}

function memoryGb(value: unknown) {
  const gb = safeNumber(value, ['memory_gb', 'memoryGb', 'memoryGB', 'memory'])
  if (gb === null) {
    const mb = safeNumber(value, ['memory_mb', 'memoryMb', 'memoryMB'])
    return mb === null ? null : mb / 1024
  }
  return gb
}

function capacityGb(value: unknown) {
  const gb = safeNumber(value, ['capacity_gb', 'capacityGb', 'capacityGB', 'capacity'])
  if (gb === null) {
    const bytes = safeNumber(value, ['capacity_bytes', 'capacityBytes'])
    return bytes === null ? null : bytes / 1024 / 1024 / 1024
  }
  return gb
}

function freeGb(value: unknown) {
  const gb = safeNumber(value, ['free_gb', 'freeGb', 'freeGB', 'free'])
  if (gb === null) {
    const bytes = safeNumber(value, ['free_bytes', 'freeBytes'])
    return bytes === null ? null : bytes / 1024 / 1024 / 1024
  }
  return gb
}

function datastoreUsedPercent(value: unknown, capacity: number | null, free: number | null) {
  const direct = safeNumber(value, ['used_percent', 'usedPercent', 'usage_percent', 'usagePercent', 'used_pct'])
  if (direct !== null) return direct
  if (capacity && free !== null && capacity > 0) return ((capacity - free) / capacity) * 100
  return null
}

export function normalizeVm(value: unknown): NormalizedVm {
  return {
    kind: 'vms',
    name: safeText(value, ['name', 'vm_name', 'vmName']),
    powerState: safeText(value, ['power_state', 'powerState', 'state', 'status'], 'unknown'),
    cpu: safeNumber(value, ['cpu', 'cpus', 'num_cpu', 'numCpu', 'cpu_count']),
    memoryGb: memoryGb(value),
    guestOs: safeText(value, ['guest_os', 'guestOs', 'guest_full_name', 'guestFullName', 'os']),
    ipAddress: safeText(value, ['ip_address', 'ipAddress', 'ip', 'guest_ip']),
    host: safeText(value, ['host', 'host_name', 'hostName']),
    datastore: safeText(value, ['datastore', 'datastore_name', 'datastoreName']),
    toolsStatus: safeText(value, ['tools_status', 'toolsStatus', 'vmware_tools', 'tools'], 'unknown'),
    raw: value,
  }
}

export function normalizeHost(value: unknown): NormalizedHost {
  return {
    kind: 'hosts',
    name: safeText(value, ['name', 'host', 'hostname']),
    connectionState: safeText(value, ['connection_state', 'connectionState', 'status', 'state'], 'unknown'),
    powerState: safeText(value, ['power_state', 'powerState'], 'unknown'),
    version: safeText(value, ['version', 'esxi_version']),
    build: safeText(value, ['build', 'build_number']),
    vendor: safeText(value, ['vendor']),
    model: safeText(value, ['model']),
    cpuCores: safeNumber(value, ['cpu_cores', 'cpuCores', 'cores', 'num_cpu_cores']),
    memoryGb: memoryGb(value),
    vmCount: safeNumber(value, ['vm_count', 'vmCount', 'vms']),
    raw: value,
  }
}

export function normalizeDatastoreHealth(value: unknown) {
  return {
    name: safeText(value, ['name', 'datastore', 'datastore_name']),
    health: statusValue(value, 'unknown'),
    accessible: safeText(value, ['accessible', 'is_accessible'], 'unknown'),
    message: safeText(value, ['message', 'reason', 'detail', 'details'], ''),
    raw: value,
  }
}

export function normalizeDatastore(value: unknown, healthByName: Map<string, ReturnType<typeof normalizeDatastoreHealth>>): NormalizedDatastore {
  const name = safeText(value, ['name', 'datastore', 'datastore_name'])
  const health = healthByName.get(name.toLowerCase())
  const capacity = capacityGb(value)
  const free = freeGb(value)
  return {
    kind: 'datastores',
    name,
    type: safeText(value, ['type', 'summary_type', 'ds_type']),
    capacityGb: capacity,
    freeGb: free,
    usedPercent: datastoreUsedPercent(health?.raw ?? value, capacity, free),
    health: health?.health ?? statusValue(value, 'unknown'),
    accessible: health?.accessible ?? safeText(value, ['accessible', 'is_accessible'], 'unknown'),
    message: health?.message ?? safeText(value, ['message', 'reason', 'detail', 'details'], ''),
    raw: { inventory: value, health: health?.raw },
  }
}

export function normalizeVms(payload: unknown) {
  return arrayFrom(payload).map(normalizeVm)
}

export function normalizeHosts(payload: unknown) {
  return arrayFrom(payload).map(normalizeHost)
}

export function normalizeDatastores(payload: unknown, healthPayload: unknown) {
  const healthMap = new Map(
    arrayFrom(healthPayload)
      .map(normalizeDatastoreHealth)
      .filter((item) => item.name !== '—')
      .map((item) => [item.name.toLowerCase(), item] as const),
  )
  return arrayFrom(payload).map((item) => normalizeDatastore(item, healthMap))
}

export function objectEntries(value: unknown) {
  return Object.entries(objectFrom(value)).filter(([, item]) => typeof item !== 'object' || item === null)
}
