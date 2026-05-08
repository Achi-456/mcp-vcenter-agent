"use client"

import { useState } from "react"
import Link from "next/link"
import { useInventory } from "@/providers/inventory-provider"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { AIAssistantPanel } from "@/components/chat/ai-assistant-panel"
import {
  Monitor, Server, HardDrive, Bell, AlertTriangle,
  Activity, Zap, BarChart3, Clock, Network, Cpu, RefreshCw
} from "lucide-react"

function SkeletonCard() {
  return (
    <Card className="border-border bg-card p-4 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-muted" />
        <div className="h-3 w-20 bg-muted rounded" />
      </div>
      <div className="mt-2 h-7 w-16 bg-muted rounded" />
      <div className="mt-1 h-3 w-24 bg-muted rounded" />
    </Card>
  )
}

export default function DashboardPage() {
  const { overview, vms, datastores, alarms, events, refreshAll } = useInventory()
  const [assistantOpen, setAssistantOpen] = useState(true)

  const isLoading = overview.isInitialLoading
  const isRefreshing = overview.isRefreshing
  const ov = overview.data
  const vmList = vms.data || []
  const dsList = datastores.data || []
  const alarmList = alarms.data || []
  const eventList = events.data || []

  return (
    <div className={cn("space-y-6 transition-all", assistantOpen ? "mr-[380px]" : "")}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-xs text-muted-foreground">vCenter infrastructure overview</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {ov?.collected_at && (
            <span>Last updated: {new Date(ov.collected_at).toLocaleTimeString()}</span>
          )}
          {isRefreshing && <Badge variant="secondary" className="text-[10px]"><RefreshCw className="mr-1 h-2.5 w-2.5 animate-spin" />Refreshing</Badge>}
          {ov?.cached && <Badge variant="secondary" className="text-[10px]">cached</Badge>}
          <Button variant="outline" size="sm" onClick={refreshAll} disabled={isRefreshing}>
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isRefreshing && "animate-spin")} />Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {isLoading ? (
          <>{Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}</>
        ) : (
          <>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/20">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600/20"><Monitor className="h-3.5 w-3.5 text-emerald-400" /></div>
                <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Total VMs</span>
              </div>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{ov?.vms.total ?? 0}</p>
              <p className="text-[11px] text-muted-foreground">{ov ? `${ov.vms.powered_on} on · ${ov.vms.powered_off} off` : ""}</p>
            </Card>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/20">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-600/20"><Zap className="h-3.5 w-3.5 text-green-400" /></div>
                <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Powered On</span>
              </div>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{ov?.vms.powered_on ?? 0}</p>
              <p className="text-[11px] text-muted-foreground">{ov?.vms.suspended ? `${ov.vms.suspended} suspended` : ""}</p>
            </Card>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/20">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-600/20"><Server className="h-3.5 w-3.5 text-cyan-400" /></div>
                <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">ESXi Hosts</span>
              </div>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{ov?.hosts.total ?? 0}</p>
              <p className="text-[11px] text-muted-foreground">{ov ? `${ov.hosts.connected} connected` : ""}</p>
            </Card>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/20">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-600/20"><Bell className="h-3.5 w-3.5 text-red-400" /></div>
                <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Active Alarms</span>
              </div>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{ov?.alarms?.total ?? 0}</p>
              <p className="text-[11px] text-muted-foreground">{ov?.alarms ? `${ov.alarms.critical} critical` : ""}</p>
            </Card>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/20">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-600/20"><HardDrive className="h-3.5 w-3.5 text-amber-400" /></div>
                <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Datastore Used</span>
              </div>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{ov ? `${ov.datastores.used_percent}%` : "0%"}</p>
              <p className="text-[11px] text-muted-foreground">{ov ? `${ov.datastores.free_gb.toFixed(0)} GB free` : ""}</p>
            </Card>
          </>
        )}
      </div>

      {/* Error banner */}
      {(overview.error || vms.error) && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {overview.error || vms.error}
        </Card>
      )}

      {/* Panels */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        {/* VM Mini Table */}
        <Card className="border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Monitor className="h-3.5 w-3.5 text-emerald-400" />
              <h3 className="text-sm font-semibold">Virtual Machines</h3>
            </div>
            <Link href="/inventory" className="text-[11px] text-emerald-400 hover:underline">View All</Link>
          </div>
          <div className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[10px]">Name</TableHead>
                  <TableHead className="text-[10px]">Power</TableHead>
                  <TableHead className="text-[10px]">CPU</TableHead>
                  <TableHead className="text-[10px]">Memory</TableHead>
                  <TableHead className="text-[10px]">IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vmList.slice(0, 5).map(vm => (
                  <TableRow key={vm.id}>
                    <TableCell className="text-xs font-medium font-mono-code">{vm.name}</TableCell>
                    <TableCell><Badge variant={vm.power_state === "poweredOn" ? "default" : "secondary"} className="text-[9px]">{vm.power_state}</Badge></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{vm.cpu} vCPU</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{vm.memory_gb} GB</TableCell>
                    <TableCell className="text-xs font-mono-code text-muted-foreground">{vm.ip_address || "-"}</TableCell>
                  </TableRow>
                ))}
                {vmList.length === 0 && !vms.isInitialLoading && (
                  <TableRow><TableCell colSpan={5} className="text-xs text-muted-foreground text-center py-4">No VMs found</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </Card>

        {/* Datastore Usage */}
        <Card className="border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <HardDrive className="h-3.5 w-3.5 text-amber-400" />
              <h3 className="text-sm font-semibold">Datastore Usage</h3>
            </div>
            <Link href="/inventory?tab=datastores" className="text-[11px] text-emerald-400 hover:underline">View All</Link>
          </div>
          <div className="px-4 py-3 space-y-3">
            {dsList.map(ds => (
              <div key={ds.id} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-mono-code text-muted-foreground">{ds.name}</span>
                  <span className={cn(ds.used_percent > 85 ? "text-red-400" : ds.used_percent > 70 ? "text-amber-400" : "text-muted-foreground")}>
                    {ds.free_gb.toFixed(0)} GB free / {ds.capacity_gb.toFixed(0)} GB
                  </span>
                </div>
                <div className="h-2 rounded-full bg-secondary overflow-hidden">
                  <div className={cn("h-full rounded-full transition-all", ds.used_percent > 85 ? "bg-red-500" : ds.used_percent > 70 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${Math.min(ds.used_percent, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Active Alarms */}
        <Card className="border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Bell className="h-3.5 w-3.5 text-red-400" />
              <h3 className="text-sm font-semibold">Active Alarms</h3>
            </div>
            <Link href="/monitoring" className="text-[11px] text-emerald-400 hover:underline">View All</Link>
          </div>
          <div className="px-4 py-3 space-y-2">
            {alarmList.slice(0, 5).map(a => (
              <div key={a.id} className="flex items-center gap-2 text-xs">
                <AlertTriangle className={cn("h-3 w-3", a.severity === "critical" || a.severity === "red" ? "text-red-400" : "text-amber-400")} />
                <span className="font-medium text-sidebar-foreground flex-1">{a.name}</span>
                <span className="text-muted-foreground">{a.entity}</span>
                <Badge variant="outline" className="text-[9px]">{a.severity}</Badge>
              </div>
            ))}
            {alarmList.length === 0 && !alarms.isInitialLoading && (
              <p className="text-xs text-muted-foreground text-center py-2">No active alarms</p>
            )}
          </div>
        </Card>

        {/* Recent Events */}
        <Card className="border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5 text-blue-400" />
              <h3 className="text-sm font-semibold">Recent Events</h3>
            </div>
            <Link href="/monitoring" className="text-[11px] text-emerald-400 hover:underline">View All</Link>
          </div>
          <div className="px-4 py-3 space-y-2 max-h-[200px] overflow-y-auto">
            {eventList.slice(0, 10).map(e => (
              <div key={e.id} className="flex items-start gap-2 text-xs">
                <div className={cn("mt-0.5 h-1.5 w-1.5 rounded-full flex-shrink-0", e.severity === "error" ? "bg-red-500" : e.severity === "warning" ? "bg-amber-500" : "bg-blue-500")} />
                <div className="min-w-0">
                  <p className="text-muted-foreground truncate">{e.message}</p>
                  <p className="text-[10px] text-muted-foreground/60">{e.entity} · {e.created_at ? new Date(e.created_at).toLocaleString() : ""}</p>
                </div>
              </div>
            ))}
            {eventList.length === 0 && !events.isInitialLoading && (
              <p className="text-xs text-muted-foreground text-center py-2">No recent events</p>
            )}
          </div>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: "/chat", label: "AI Chat", icon: BotIcon, desc: "Agent conversation" },
          { href: "/inventory", label: "Inventory", icon: Server, desc: "Browse all resources" },
          { href: "/monitoring", label: "Monitoring", icon: BarChart3, desc: "Alarms & events" },
          { href: "/settings", label: "Settings", icon: Cpu, desc: "Configure vCenter & LLM" },
        ].map(link => (
          <Link key={link.href} href={link.href}>
            <Card className="border-border bg-card p-4 transition-colors hover:border-emerald-600/30 cursor-pointer">
              <link.icon className="h-4 w-4 text-emerald-400 mb-2" />
              <h4 className="text-sm font-semibold">{link.label}</h4>
              <p className="text-[11px] text-muted-foreground">{link.desc}</p>
            </Card>
          </Link>
        ))}
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
