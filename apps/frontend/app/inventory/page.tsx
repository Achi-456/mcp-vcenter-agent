"use client"

import { useEffect, useState, useCallback } from "react"
import { api, type VM, type Host, type Datastore, type NetworkItem, type InventoryOverview } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { RefreshCw, Server, HardDrive, Network, Monitor, Settings } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

const tabs = ["vms", "hosts", "datastores", "networks"] as const
type Tab = (typeof tabs)[number]

export default function InventoryPage() {
  const [active, setActive] = useState<Tab>("vms")
  const [vms, setVMs] = useState<VM[]>([])
  const [hosts, setHosts] = useState<Host[]>([])
  const [datastores, setDatastores] = useState<Datastore[]>([])
  const [networks, setNetworks] = useState<NetworkItem[]>([])
  const [overview, setOverview] = useState<InventoryOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ code?: string; message: string } | null>(null)
  const [cached, setCached] = useState(false)
  const [collectedAt, setCollectedAt] = useState<string | null>(null)

  const fetchTab = useCallback(async (tab: Tab) => {
    setLoading(true)
    setError(null)
    try {
      if (tab === "vms") { const d = await api.getVMs(); setVMs(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }
      if (tab === "hosts") { const d = await api.getHosts(); setHosts(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }
      if (tab === "datastores") { const d = await api.getDatastores(); setDatastores(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }
      if (tab === "networks") { const d = await api.getNetworks(); setNetworks(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to fetch"
      if (msg.includes("409") || msg.includes("VCENTER")) {
        setError({ code: "VCENTER_NOT_CONFIGURED", message: "vCenter is not configured. Configure credentials in Settings first." })
      } else {
        setError({ message: msg })
      }
    } finally { setLoading(false) }
  }, [])

  const fetchOverview = useCallback(async () => {
    try {
      const o = await api.getInventoryOverview()
      setOverview(o)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchOverview() }, [fetchOverview])
  useEffect(() => { fetchTab(active) }, [active, fetchTab])

  const refresh = () => {
    if (active === "vms") api.getVMs(true).then(d => { setVMs(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }).catch(() => {})
    if (active === "hosts") api.getHosts(true).then(d => { setHosts(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }).catch(() => {})
    if (active === "datastores") api.getDatastores(true).then(d => { setDatastores(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }).catch(() => {})
    if (active === "networks") api.getNetworks().then(d => { setNetworks(d.items); setCached(d.cached); setCollectedAt(d.collected_at) }).catch(() => {})
    fetchOverview()
  }

  if (error?.code === "VCENTER_NOT_CONFIGURED") {
    return (
      <div className="space-y-6">
        <div><h1 className="text-lg font-semibold">Inventory</h1></div>
        <Card className="border-dashed border-border p-12 text-center">
          <Server className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{error.message}</p>
          <Link href="/settings">
            <Button variant="outline" size="sm" className="mt-4">
              <Settings className="mr-1.5 h-3.5 w-3.5" /> Open Settings
            </Button>
          </Link>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Inventory</h1>
          <p className="text-xs text-muted-foreground">
            vCenter resource browser
            {collectedAt && ` · ${new Date(collectedAt).toLocaleTimeString()}`}
            {cached && <Badge variant="secondary" className="ml-2 text-[10px]">cached</Badge>}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Card className="border-border bg-card p-3">
            <div className="flex items-center gap-2"><Monitor className="h-3.5 w-3.5 text-emerald-400" /><span className="text-xs text-muted-foreground">VMs</span></div>
            <p className="mt-1 text-lg font-semibold">{overview.vms.total}</p>
            <p className="text-[11px] text-muted-foreground">{overview.vms.powered_on} on · {overview.vms.powered_off} off</p>
          </Card>
          <Card className="border-border bg-card p-3">
            <div className="flex items-center gap-2"><Server className="h-3.5 w-3.5 text-cyan-400" /><span className="text-xs text-muted-foreground">Hosts</span></div>
            <p className="mt-1 text-lg font-semibold">{overview.hosts.total}</p>
            <p className="text-[11px] text-muted-foreground">{overview.hosts.connected} connected</p>
          </Card>
          <Card className="border-border bg-card p-3">
            <div className="flex items-center gap-2"><HardDrive className="h-3.5 w-3.5 text-amber-400" /><span className="text-xs text-muted-foreground">Datastores</span></div>
            <p className="mt-1 text-lg font-semibold">{overview.datastores.total}</p>
            <p className="text-[11px] text-muted-foreground">{overview.datastores.used_percent}% used</p>
          </Card>
          <Card className="border-border bg-card p-3">
            <div className="flex items-center gap-2"><Network className="h-3.5 w-3.5 text-blue-400" /><span className="text-xs text-muted-foreground">Networks</span></div>
            <p className="mt-1 text-lg font-semibold">{overview.networks.total}</p>
          </Card>
          <Card className="border-border bg-card p-3">
            <div className="flex items-center gap-2"><HardDrive className="h-3.5 w-3.5 text-purple-400" /><span className="text-xs text-muted-foreground">Capacity</span></div>
            <p className="mt-1 text-lg font-semibold">{overview.datastores.capacity_gb.toFixed(0)} GB</p>
            <p className="text-[11px] text-muted-foreground">{overview.datastores.free_gb.toFixed(0)} GB free</p>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button key={t} onClick={() => setActive(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              active === t ? "border-emerald-500 text-emerald-400" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {t === "vms" ? "VMs" : t === "hosts" ? "Hosts" : t === "datastores" ? "Datastores" : "Networks"}
          </button>
        ))}
      </div>

      {error && !error.code && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error.message}</Card>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                {active === "vms" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Power</TableHead><TableHead className="text-xs">CPU</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">OS</TableHead><TableHead className="text-xs">IP</TableHead><TableHead className="text-xs">Host</TableHead><TableHead className="text-xs">Tools</TableHead></>}
                {active === "hosts" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Connection</TableHead><TableHead className="text-xs">CPU</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">VMs</TableHead><TableHead className="text-xs">Version</TableHead></>}
                {active === "datastores" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Type</TableHead><TableHead className="text-xs">Capacity</TableHead><TableHead className="text-xs">Free</TableHead><TableHead className="text-xs">Used %</TableHead><TableHead className="text-xs">Accessible</TableHead></>}
                {active === "networks" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Type</TableHead><TableHead className="text-xs">Accessible</TableHead></>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {active === "vms" && vms.map((vm) => (
                <TableRow key={vm.id}>
                  <TableCell className="text-sm font-medium font-mono-code">{vm.name}</TableCell>
                  <TableCell><Badge variant={vm.power_state === "poweredOn" ? "default" : "secondary"} className="text-[10px]">{vm.power_state}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{vm.cpu} vCPU</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{vm.memory_gb} GB</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{vm.guest_os || "-"}</TableCell>
                  <TableCell className="text-sm font-mono-code text-muted-foreground">{vm.ip_address || "-"}</TableCell>
                  <TableCell className="text-sm font-mono-code text-muted-foreground">{vm.host || "-"}</TableCell>
                  <TableCell><Badge variant={vm.tools_status === "toolsOk" ? "default" : "secondary"} className="text-[10px]">{vm.tools_status || "unknown"}</Badge></TableCell>
                </TableRow>
              ))}
              {active === "hosts" && hosts.map((h) => (
                <TableRow key={h.id}>
                  <TableCell className="text-sm font-medium font-mono-code">{h.name}</TableCell>
                  <TableCell><Badge variant="outline" className="text-[10px]">{h.connection_state}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.cpu_cores} core × {h.cpu_threads} thread</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.memory_gb} GB</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.vm_count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.version || "-"}</TableCell>
                </TableRow>
              ))}
              {active === "datastores" && datastores.map((ds) => (
                <TableRow key={ds.id}>
                  <TableCell className="text-sm font-medium font-mono-code">{ds.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{ds.type}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{ds.capacity_gb.toFixed(0)} GB</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{ds.free_gb.toFixed(0)} GB</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-secondary">
                        <div className={cn("h-full rounded-full", ds.used_percent > 80 ? "bg-red-500" : ds.used_percent > 60 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${Math.min(ds.used_percent, 100)}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground">{ds.used_percent}%</span>
                    </div>
                  </TableCell>
                  <TableCell><Badge variant={ds.accessible ? "default" : "destructive"} className="text-[10px]">{ds.accessible ? "Yes" : "No"}</Badge></TableCell>
                </TableRow>
              ))}
              {active === "networks" && networks.map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="text-sm font-medium font-mono-code">{n.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{n.type}</TableCell>
                  <TableCell><Badge variant={n.accessible ? "default" : "destructive"} className="text-[10px]">{n.accessible ? "Yes" : "No"}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
