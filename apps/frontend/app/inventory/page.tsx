"use client"

import { useEffect, useState } from "react"
import { api, type VM, type Host, type Datastore } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { RefreshCw, Server, HardDrive } from "lucide-react"

const tabs = ["vms", "hosts", "datastores"] as const
type Tab = (typeof tabs)[number]

export default function InventoryPage() {
  const [active, setActive] = useState<Tab>("vms")
  const [vms, setVMs] = useState<VM[]>([])
  const [hosts, setHosts] = useState<Host[]>([])
  const [datastores, setDatastores] = useState<Datastore[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      if (active === "vms") { const d = await api.getVMs(); setVMs(d.items) }
      if (active === "hosts") { const d = await api.getHosts(); setHosts(d.items) }
      if (active === "datastores") { const d = await api.getDatastores(); setDatastores(d.items) }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fetch failed")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [active])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Inventory</h1>
          <p className="text-xs text-muted-foreground">vCenter resource browser</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetch} disabled={loading}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              active === t ? "border-emerald-500 text-emerald-400" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "vms" ? "VMs" : t === "hosts" ? "Hosts" : "Datastores"}
          </button>
        ))}
      </div>

      {error && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</Card>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                {active === "vms" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">State</TableHead><TableHead className="text-xs">CPU</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">Host</TableHead><TableHead className="text-xs">IP</TableHead></>}
                {active === "hosts" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">State</TableHead><TableHead className="text-xs">CPU Cores</TableHead><TableHead className="text-xs">Memory</TableHead><TableHead className="text-xs">VMs</TableHead></>}
                {active === "datastores" && <><TableHead className="text-xs">Name</TableHead><TableHead className="text-xs">Type</TableHead><TableHead className="text-xs">Capacity</TableHead><TableHead className="text-xs">Free</TableHead><TableHead className="text-xs">Used %</TableHead></>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {active === "vms" && vms.map((vm) => (
                <TableRow key={vm.moid}>
                  <TableCell className="text-sm font-medium font-mono-code">{vm.name}</TableCell>
                  <TableCell>
                    <Badge variant={vm.power_state === "poweredOn" ? "default" : "secondary"} className="text-[10px]">
                      {vm.power_state}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{vm.cpu} vCPU</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{vm.memory_mb} MB</TableCell>
                  <TableCell className="text-sm font-mono-code text-muted-foreground">{vm.host || "-"}</TableCell>
                  <TableCell className="text-sm font-mono-code text-muted-foreground">{vm.ip_address || "-"}</TableCell>
                </TableRow>
              ))}
              {active === "hosts" && hosts.map((h) => (
                <TableRow key={h.moid}>
                  <TableCell className="text-sm font-medium font-mono-code">{h.name}</TableCell>
                  <TableCell><Badge variant="outline" className="text-[10px]">{h.connection_state}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.cpu_cores}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{(h.memory_mb / 1024).toFixed(1)} GB</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{h.num_vms}</TableCell>
                </TableRow>
              ))}
              {active === "datastores" && datastores.map((ds) => {
                const used = ((ds.capacity_gb - ds.free_gb) / ds.capacity_gb * 100) || 0
                return (
                  <TableRow key={ds.moid}>
                    <TableCell className="text-sm font-medium font-mono-code">{ds.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ds.type}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ds.capacity_gb.toFixed(1)} GB</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ds.free_gb.toFixed(1)} GB</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 rounded-full bg-secondary">
                          <div className={cn("h-full rounded-full", used > 80 ? "bg-red-500" : used > 60 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${Math.min(used, 100)}%` }} />
                        </div>
                        <span className="text-xs text-muted-foreground">{used.toFixed(0)}%</span>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

import { cn } from "@/lib/utils"
