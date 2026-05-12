'use client'

import { useCallback, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { firstUpdated, formatDate, isRefreshing, refreshAll } from '@/lib/dashboard-data'
import {
  formatGb,
  formatPercent,
  normalizeDatastores,
  normalizeHosts,
  normalizeVms,
  type InventoryKind,
  type InventoryRow,
  type NormalizedDatastore,
  type NormalizedHost,
  type NormalizedVm,
} from '@/lib/inventory-data'
import { DetailsDrawer, InventoryStatus, InventoryTable, InventoryTabs, InventoryToolbar, ProgressBar, type Column, type SortDirection } from '@/components/inventory'
import { ErrorState, LoadingState, MetricCard, PageHeader, RefreshButton, SectionCard, StatusBadge } from '@/components/ui'
import { useApiResource } from '@/hooks/use-api-resource'

const REFRESH_INTERVAL_MS = 120000

function lower(value: string | number | null) {
  return String(value ?? '').toLowerCase()
}

function includesAny(row: string[], query: string) {
  if (!query.trim()) return true
  const normalized = query.toLowerCase()
  return row.some((value) => value.toLowerCase().includes(normalized))
}

function compareValues(a: string | number | null, b: string | number | null, direction: SortDirection) {
  const multiplier = direction === 'asc' ? 1 : -1
  if (typeof a === 'number' && typeof b === 'number') return (a - b) * multiplier
  return lower(a).localeCompare(lower(b)) * multiplier
}

function sortRows<Row>(rows: Row[], sortKey: string, direction: SortDirection, selector: (row: Row, key: string) => string | number | null) {
  return [...rows].sort((a, b) => compareValues(selector(a, sortKey), selector(b, sortKey), direction))
}

function useSort(defaultKey: string) {
  const [sortKey, setSortKey] = useState(defaultKey)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const onSort = (key: string) => {
    if (key === sortKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }
  return { sortKey, sortDirection, onSort }
}

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<InventoryKind>('vms')
  const [selectedRow, setSelectedRow] = useState<InventoryRow | null>(null)
  const [search, setSearch] = useState('')
  const [powerFilter, setPowerFilter] = useState('all')
  const [toolsFilter, setToolsFilter] = useState('all')
  const [connectionFilter, setConnectionFilter] = useState('all')
  const [healthFilter, setHealthFilter] = useState('all')
  const [accessibleFilter, setAccessibleFilter] = useState('all')
  const vmSort = useSort('name')
  const hostSort = useSort('name')
  const datastoreSort = useSort('name')

  const vmsResource = useApiResource(useCallback(() => api.getVms(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const hostsResource = useApiResource(useCallback(() => api.getHosts(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const datastoresResource = useApiResource(useCallback(() => api.getDatastores(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const datastoreHealth = useApiResource(useCallback(() => api.getDatastoreHealth(), []), { refreshIntervalMs: REFRESH_INTERVAL_MS })
  const resources = useMemo(() => [vmsResource, hostsResource, datastoresResource, datastoreHealth], [vmsResource, hostsResource, datastoresResource, datastoreHealth])
  const refreshing = isRefreshing(resources)
  const lastUpdated = firstUpdated(resources)

  const vms = useMemo(() => normalizeVms(vmsResource.data), [vmsResource.data])
  const hosts = useMemo(() => normalizeHosts(hostsResource.data), [hostsResource.data])
  const datastores = useMemo(() => normalizeDatastores(datastoresResource.data, datastoreHealth.data), [datastoresResource.data, datastoreHealth.data])

  const filteredVms = useMemo(() => {
    const rows = vms.filter((vm) => {
      const powerMatch = powerFilter === 'all' || lower(vm.powerState).includes(powerFilter.toLowerCase())
      const toolsMatch =
        toolsFilter === 'all' ||
        (toolsFilter === 'toolsOk' && (lower(vm.toolsStatus).includes('ok') || lower(vm.toolsStatus).includes('running'))) ||
        (toolsFilter === 'toolsNotRunning' && lower(vm.toolsStatus).includes('not')) ||
        (toolsFilter === 'unknown' && lower(vm.toolsStatus).includes('unknown'))
      return powerMatch && toolsMatch && includesAny([vm.name, vm.ipAddress, vm.host, vm.datastore, vm.guestOs], search)
    })
    return sortRows(rows, vmSort.sortKey, vmSort.sortDirection, (vm, key) => {
      const values: Record<string, string | number | null> = {
        name: vm.name,
        power: vm.powerState,
        cpu: vm.cpu,
        memory: vm.memoryGb,
        host: vm.host,
        datastore: vm.datastore,
      }
      return values[key] ?? vm.name
    })
  }, [powerFilter, search, toolsFilter, vmSort.sortDirection, vmSort.sortKey, vms])

  const filteredHosts = useMemo(() => {
    const rows = hosts.filter((host) => {
      const connectionMatch = connectionFilter === 'all' || lower(host.connectionState).includes(connectionFilter.toLowerCase())
      return connectionMatch && includesAny([host.name, host.version, host.vendor, host.model], search)
    })
    return sortRows(rows, hostSort.sortKey, hostSort.sortDirection, (host, key) => {
      const values: Record<string, string | number | null> = {
        name: host.name,
        connection: host.connectionState,
        cpu: host.cpuCores,
        memory: host.memoryGb,
        vmCount: host.vmCount,
      }
      return values[key] ?? host.name
    })
  }, [connectionFilter, hostSort.sortDirection, hostSort.sortKey, hosts, search])

  const filteredDatastores = useMemo(() => {
    const rows = datastores.filter((datastore) => {
      const healthMatch = healthFilter === 'all' || lower(datastore.health).includes(healthFilter)
      const accessibleMatch =
        accessibleFilter === 'all' ||
        (accessibleFilter === 'accessible' && lower(datastore.accessible).includes('true')) ||
        (accessibleFilter === 'inaccessible' && (lower(datastore.accessible).includes('false') || lower(datastore.accessible).includes('inaccessible')))
      return healthMatch && accessibleMatch && includesAny([datastore.name, datastore.type], search)
    })
    return sortRows(rows, datastoreSort.sortKey, datastoreSort.sortDirection, (datastore, key) => {
      const values: Record<string, string | number | null> = {
        name: datastore.name,
        capacity: datastore.capacityGb,
        free: datastore.freeGb,
        used: datastore.usedPercent,
        health: datastore.health,
      }
      return values[key] ?? datastore.name
    })
  }, [accessibleFilter, datastoreSort.sortDirection, datastoreSort.sortKey, datastores, healthFilter, search])

  const vmColumns: Array<Column<NormalizedVm>> = [
    { key: 'name', label: 'Name', sortable: true, render: (row) => <span className="font-mono text-xs font-semibold text-ops-ink">{row.name}</span> },
    { key: 'power', label: 'Power State', sortable: true, render: (row) => <InventoryStatus status={row.powerState} /> },
    { key: 'cpu', label: 'CPU', sortable: true, render: (row) => row.cpu ?? '—' },
    { key: 'memory', label: 'Memory', sortable: true, render: (row) => formatGb(row.memoryGb) },
    { key: 'guest', label: 'Guest OS', render: (row) => row.guestOs },
    { key: 'ip', label: 'IP Address', render: (row) => row.ipAddress },
    { key: 'host', label: 'Host', sortable: true, render: (row) => row.host },
    { key: 'datastore', label: 'Datastore', sortable: true, render: (row) => row.datastore },
    { key: 'tools', label: 'VMware Tools', render: (row) => <InventoryStatus status={row.toolsStatus} /> },
  ]

  const hostColumns: Array<Column<NormalizedHost>> = [
    { key: 'name', label: 'Name', sortable: true, render: (row) => <span className="font-mono text-xs font-semibold text-ops-ink">{row.name}</span> },
    { key: 'connection', label: 'Connection State', sortable: true, render: (row) => <InventoryStatus status={row.connectionState} /> },
    { key: 'power', label: 'Power State', render: (row) => <InventoryStatus status={row.powerState} /> },
    { key: 'version', label: 'Version', render: (row) => row.version },
    { key: 'build', label: 'Build', render: (row) => row.build },
    { key: 'vendor', label: 'Vendor', render: (row) => row.vendor },
    { key: 'model', label: 'Model', render: (row) => row.model },
    { key: 'cpu', label: 'CPU Cores', sortable: true, render: (row) => row.cpuCores ?? '—' },
    { key: 'memory', label: 'Memory', sortable: true, render: (row) => formatGb(row.memoryGb) },
    { key: 'vmCount', label: 'VM Count', sortable: true, render: (row) => row.vmCount ?? '—' },
  ]

  const datastoreColumns: Array<Column<NormalizedDatastore>> = [
    { key: 'name', label: 'Name', sortable: true, render: (row) => <span className="font-mono text-xs font-semibold text-ops-ink">{row.name}</span> },
    { key: 'type', label: 'Type', render: (row) => row.type },
    { key: 'capacity', label: 'Capacity GB', sortable: true, render: (row) => formatGb(row.capacityGb) },
    { key: 'free', label: 'Free GB', sortable: true, render: (row) => formatGb(row.freeGb) },
    { key: 'used', label: 'Used %', sortable: true, render: (row) => <ProgressBar value={row.usedPercent} /> },
    { key: 'health', label: 'Health', sortable: true, render: (row) => <InventoryStatus status={row.health} /> },
    { key: 'accessible', label: 'Accessible', render: (row) => <InventoryStatus status={row.accessible} /> },
  ]

  const criticalDatastores = datastores.filter((datastore) => lower(datastore.health).includes('critical')).length
  const poweredOn = vms.filter((vm) => lower(vm.powerState).includes('poweredon')).length
  const poweredOff = vms.filter((vm) => lower(vm.powerState).includes('poweredoff')).length

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory"
        title="Inventory"
        description="Browse vCenter virtual machines, ESXi hosts, and datastores."
        action={<RefreshButton onRefresh={() => refreshAll(resources)} isRefreshing={refreshing} />}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ops-steel/10 bg-white px-4 py-3 text-sm text-ops-muted shadow-card">
        <StatusBadge status={refreshing ? 'refreshing' : 'healthy'} />
        <span>Auto-refresh every 2 minutes.</span>
        <span>Last updated: {formatDate(lastUpdated)}</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard title="Total VMs" value={vms.length || '—'} />
        <MetricCard title="Powered On VMs" value={poweredOn || '—'} status="online" />
        <MetricCard title="Powered Off VMs" value={poweredOff || '—'} status="offline" />
        <MetricCard title="Hosts" value={hosts.length || '—'} />
        <MetricCard title="Datastores" value={datastores.length || '—'} />
        <MetricCard title="Critical Datastores" value={criticalDatastores} status={criticalDatastores ? 'critical' : 'clear'} />
      </div>

      <InventoryTabs active={activeTab} onChange={setActiveTab} />

      <SectionCard title={activeTab === 'vms' ? 'Virtual Machines' : activeTab === 'hosts' ? 'Hosts' : 'Datastores'}>
        {(activeTab === 'vms' && vmsResource.isLoading) || (activeTab === 'hosts' && hostsResource.isLoading) || (activeTab === 'datastores' && datastoresResource.isLoading) ? (
          <LoadingState label="Loading inventory..." />
        ) : null}

        {activeTab === 'vms' && vmsResource.error ? <ErrorState message={vmsResource.error} code={vmsResource.errorCode} /> : null}
        {activeTab === 'hosts' && hostsResource.error ? <ErrorState message={hostsResource.error} code={hostsResource.errorCode} /> : null}
        {activeTab === 'datastores' && (datastoresResource.error || datastoreHealth.error) ? (
          <ErrorState message={datastoresResource.error ?? datastoreHealth.error ?? 'Datastore data unavailable.'} code={datastoresResource.errorCode ?? datastoreHealth.errorCode} />
        ) : null}

        {activeTab === 'vms' ? (
          <div className="space-y-4">
            <InventoryToolbar
              search={search}
              onSearchChange={setSearch}
              summary={`Showing ${filteredVms.length} of ${vms.length} VMs`}
              filters={[
                {
                  label: 'Power',
                  value: powerFilter,
                  onChange: setPowerFilter,
                  options: ['all', 'poweredOn', 'poweredOff', 'suspended', 'unknown'].map((value) => ({ value, label: value })),
                },
                {
                  label: 'Tools',
                  value: toolsFilter,
                  onChange: setToolsFilter,
                  options: ['all', 'toolsOk', 'toolsNotRunning', 'unknown'].map((value) => ({ value, label: value })),
                },
              ]}
            />
            <InventoryTable rows={filteredVms} columns={vmColumns} {...vmSort} onRowClick={setSelectedRow} emptyTitle="No VMs match the current filters" />
          </div>
        ) : null}

        {activeTab === 'hosts' ? (
          <div className="space-y-4">
            <InventoryToolbar
              search={search}
              onSearchChange={setSearch}
              summary={`Showing ${filteredHosts.length} of ${hosts.length} hosts`}
              filters={[
                {
                  label: 'Connection',
                  value: connectionFilter,
                  onChange: setConnectionFilter,
                  options: ['all', 'connected', 'disconnected', 'notResponding', 'unknown'].map((value) => ({ value, label: value })),
                },
              ]}
            />
            <InventoryTable rows={filteredHosts} columns={hostColumns} {...hostSort} onRowClick={setSelectedRow} emptyTitle="No hosts match the current filters" />
          </div>
        ) : null}

        {activeTab === 'datastores' ? (
          <div className="space-y-4">
            <InventoryToolbar
              search={search}
              onSearchChange={setSearch}
              summary={`Showing ${filteredDatastores.length} of ${datastores.length} datastores`}
              filters={[
                {
                  label: 'Health',
                  value: healthFilter,
                  onChange: setHealthFilter,
                  options: ['all', 'healthy', 'warning', 'critical', 'unknown'].map((value) => ({ value, label: value })),
                },
                {
                  label: 'Accessible',
                  value: accessibleFilter,
                  onChange: setAccessibleFilter,
                  options: ['all', 'accessible', 'inaccessible'].map((value) => ({ value, label: value })),
                },
              ]}
            />
            <InventoryTable
              rows={filteredDatastores}
              columns={datastoreColumns}
              {...datastoreSort}
              onRowClick={setSelectedRow}
              emptyTitle="No datastores match the current filters"
            />
          </div>
        ) : null}
      </SectionCard>

      <DetailsDrawer row={selectedRow} onClose={() => setSelectedRow(null)} />
    </div>
  )
}
