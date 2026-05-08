"use client"

import { useState, useEffect } from "react"
import { useInventory } from "@/providers/inventory-provider"
import { api, type InventoryOverview } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { AIAssistantPanel } from "@/components/chat/ai-assistant-panel"
import { RefreshCw, Server, HardDrive, Network, Monitor, Settings } from "lucide-react"
import Link from "next/link"

const tabs = ["vms", "hosts", "clusters", "datastores", "networks"] as const
type Tab = (typeof tabs)[number]

export default function InventoryPage() {
  const [active, setActive] = useState<Tab>("vms")
  const [overview, setOverview] = useState<InventoryOverview | null>(null)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const { vms, hosts, clusters, datastores, networks, refreshVMs, refreshHosts, refreshClusters, refreshDatastores, refreshNetworks } = useInventory()

  const activeCache = active === "vms" ? vms : active === "hosts" ? hosts : active === "clusters" ? clusters : active === "datastores" ? datastores : networks
  const activeItems = active === "vms" ? (vms.data || []) : active === "hosts" ? (hosts.data || []) : active === "clusters" ? (clusters.data || []) : active === "datastores" ? (datastores.data || []) : (networks.data || [])

  useEffect(() => {
    api.getInventoryOverview().then(setOverview).catch(() => {})
  }, [])

  const refresh = () => {
    if (active === "vms") refreshVMs()
    else if (active === "hosts") refreshHosts()
    else if (active === "clusters") refreshClusters()
    else if (active === "datastores") refreshDatastores()
    else if (active === "networks") refreshNetworks()
  }

  if (vms.error && !vms.data && (vms.error.includes("VCENTER") || vms.error.includes("configured"))) {
    return (
      <div className="space-y-6">
        <div><h1 className="text-lg font-semibold">Inventory</h1></div>
        <Card className="border-dashed border-border p-12 text-center">
          <Server className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{vms.error}</p>
          <Link href="/settings"><Button variant="outline" size="sm" className="mt-4"><Settings className="mr-1.5 h-3.5 w-3.5" />Open Settings</Button></Link>
        </Card>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", assistantOpen ? "mr-[380px]" : "")}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Inventory</h1>
          <p className="text-xs text-muted-foreground">
            vCenter resource browser
            {activeCache.lastUpdatedAt && ` · Last updated: ${new Date(activeCache.lastUpdatedAt).toLocaleTimeString()}`}
            {activeCache.isRefreshing && <Badge variant="secondary" className="ml-2 text-[10px]"><RefreshCw className="mr-1 h-2.5 w-2.5 animate-spin" />Refreshing</Badge>}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAssistantOpen(!assistantOpen)}>
            <BotIcon className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="sm" onClick={refresh} disabled={activeCache.isRefreshing}>
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", activeCache.isRefreshing && "animate-spin")} />Refresh
          </Button>
        </div>
      </div>

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

      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button key={t} onClick={() => setActive(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${active === t ? "border-emerald-500 text-emerald-400" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t === "vms" ? "VMs" : t === "hosts" ? "Hosts" : t === "clusters" ? "Clusters" : t === "datastores" ? "Datastores" : "Networks"}
          </button>
        ))}
      </div>

      {activeCache.error && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{activeCache.error}</Card>
      )}

      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              {active === "vms" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Power</TableHead><TableHead className="text-xs">CPU</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">OS</TableHead><TableHead className="text-xs">IP</TableHead><TableHead className="text-xs">Host</TableHead><TableHead className="text-xs">Tools</TableHead></>}
              {active === "hosts" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Connection</TableHead><TableHead className="text-xs">CPU</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">VMs</TableHead><TableHead className="text-xs">Version</TableHead></>}
              {active === "clusters" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Hosts</TableHead><TableHead className="text-xs">VMs</TableHead><TableHead className="text-xs">CPU (MHz)</TableHead><TableHead className="text-xs">Memory (MB)</TableHead></>}
              {active === "datastores" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Type</TableHead><TableHead className="text-xs">Capacity</TableHead><TableHead className="text-xs">Free</TableHead><TableHead className="text-xs">Used %</TableHead><TableHead className="text-xs">Accessible</TableHead></>}
              {active === "networks" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Type</TableHead><TableHead className="text-xs">Accessible</TableHead></>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {active === "vms" && (vms.data || []).map((vm: import("@/lib/api").VM) => (
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
            {active === "hosts" && (hosts.data || []).map((h: import("@/lib/api").Host) => (
              <TableRow key={h.id}>
                <TableCell className="text-sm font-medium font-mono-code">{h.name}</TableCell>
                <TableCell><Badge variant="outline" className="text-[10px]">{h.connection_state}</Badge></TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.cpu_cores} core x {h.cpu_threads} thread</TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.memory_gb} GB</TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.vm_count}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.version || "-"}</TableCell>
              </TableRow>
            ))}
            {active === "clusters" && (clusters.data || []).map((c: import("@/lib/api").Cluster) => (
              <TableRow key={c.id}>
                <TableCell className="text-sm font-medium font-mono-code">{c.name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{c.num_hosts}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{c.num_vms}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{c.total_cpu_mhz.toLocaleString()}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{(c.total_memory_mb / 1024).toFixed(0)} GB</TableCell>
              </TableRow>
            ))}
            {active === "datastores" && (datastores.data || []).map((ds: import("@/lib/api").Datastore) => (
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
            {active === "networks" && (networks.data || []).map((n: import("@/lib/api").NetworkItem) => (
              <TableRow key={n.id}>
                <TableCell className="text-sm font-medium font-mono-code">{n.name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{n.type}</TableCell>
                <TableCell><Badge variant={n.accessible ? "default" : "destructive"} className="text-[10px]">{n.accessible ? "Yes" : "No"}</Badge></TableCell>
              </TableRow>
            ))}
            {activeItems.length === 0 && !activeCache.isInitialLoading && (
              <TableRow><TableCell colSpan={8} className="text-xs text-muted-foreground text-center py-8">No items found</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <AIAssistantPanel visible={assistantOpen} onToggle={() => setAssistantOpen(!assistantOpen)} />
    </div>
  )
}

function BotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
      <line x1="8" y1="16" x2="8" y2="16" />
      <line x1="16" y1="16" x2="16" y2="16" />
    </svg>
  )
}
