"use client"

import { useInventory } from "@/providers/inventory-provider"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { AIAssistantPanel } from "@/components/chat/ai-assistant-panel"
import { Bell, Clock, RefreshCw, AlertTriangle, Info, XCircle, CheckCircle2, Settings } from "lucide-react"
import Link from "next/link"
import { useState } from "react"

export default function MonitoringPage() {
  const { alarms, events, refreshAlarms, refreshEvents } = useInventory()
  const [assistantOpen, setAssistantOpen] = useState(false)

  const isAnyRefreshing = alarms.isRefreshing || events.isRefreshing
  const cacheError = alarms.error || events.error

  if (alarms.error && !alarms.data && (alarms.error.includes("VCENTER") || alarms.error.includes("configured"))) {
    return (
      <div className="space-y-6">
        <div><h1 className="text-lg font-semibold">Monitoring</h1></div>
        <Card className="border-dashed border-border p-12 text-center">
          <Bell className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{alarms.error}</p>
          <Link href="/settings"><Button variant="outline" size="sm" className="mt-4"><Settings className="mr-1.5 h-3.5 w-3.5" />Open Settings</Button></Link>
        </Card>
      </div>
    )
  }

  const alarmList = alarms.data || []
  const eventList = events.data || []
  const criticalAlarms = alarmList.filter(a => a.severity === "critical" || a.severity === "red")
  const warningAlarms = alarmList.filter(a => a.severity === "warning" || a.severity === "yellow")
  const errorEvents = eventList.filter(e => e.severity === "error").length
  const warningEvents = eventList.filter(e => e.severity === "warning").length

  return (
    <div className={cn("space-y-6", assistantOpen ? "mr-[380px]" : "")}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Monitoring</h1>
          <p className="text-xs text-muted-foreground">
            vCenter alarms & events
            {(alarms.lastUpdatedAt || events.lastUpdatedAt) && ` · Last updated: ${new Date(alarms.lastUpdatedAt || events.lastUpdatedAt || "").toLocaleTimeString()}`}
            {isAnyRefreshing && <Badge variant="secondary" className="ml-2 text-[10px]"><RefreshCw className="mr-1 h-2.5 w-2.5 animate-spin" />Refreshing</Badge>}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAssistantOpen(!assistantOpen)}>
            <AssistantIcon className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => { refreshAlarms(); refreshEvents() }} disabled={isAnyRefreshing}>
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isAnyRefreshing && "animate-spin")} />Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="border-border bg-card p-3">
          <div className="flex items-center gap-2"><Bell className="h-3.5 w-3.5 text-red-400" /><span className="text-xs text-muted-foreground">Alarms</span></div>
          <p className="mt-1 text-lg font-semibold">{alarmList.length}</p>
          <p className="text-[11px] text-muted-foreground">{criticalAlarms.length} critical</p>
        </Card>
        <Card className="border-border bg-card p-3">
          <div className="flex items-center gap-2"><AlertTriangle className="h-3.5 w-3.5 text-amber-400" /><span className="text-xs text-muted-foreground">Warnings</span></div>
          <p className="mt-1 text-lg font-semibold">{warningAlarms.length}</p>
        </Card>
        <Card className="border-border bg-card p-3">
          <div className="flex items-center gap-2"><XCircle className="h-3.5 w-3.5 text-red-400" /><span className="text-xs text-muted-foreground">Events (Error)</span></div>
          <p className="mt-1 text-lg font-semibold">{errorEvents}</p>
          <p className="text-[11px] text-muted-foreground">of {eventList.length} total</p>
        </Card>
        <Card className="border-border bg-card p-3">
          <div className="flex items-center gap-2"><Info className="h-3.5 w-3.5 text-blue-400" /><span className="text-xs text-muted-foreground">Events (Warn)</span></div>
          <p className="mt-1 text-lg font-semibold">{warningEvents}</p>
        </Card>
      </div>

      {cacheError && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{cacheError}</Card>
      )}

      <Tabs defaultValue="alarms" className="w-full">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="alarms" className="text-xs"><Bell className="mr-1.5 h-3.5 w-3.5" />Alarms</TabsTrigger>
          <TabsTrigger value="events" className="text-xs"><Clock className="mr-1.5 h-3.5 w-3.5" />Events</TabsTrigger>
        </TabsList>

        <TabsContent value="alarms">
          <div className="rounded-lg border border-border overflow-hidden mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Severity</TableHead>
                  <TableHead className="text-xs">Name</TableHead>
                  <TableHead className="text-xs">Entity</TableHead>
                  <TableHead className="text-xs">Type</TableHead>
                  <TableHead className="text-xs">Acknowledged</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alarmList.map(a => (
                  <TableRow key={a.id}>
                    <TableCell><Badge variant={a.severity === "critical" || a.severity === "red" ? "destructive" : a.severity === "warning" || a.severity === "yellow" ? "default" : "secondary"} className="text-[10px]">{a.severity}</Badge></TableCell>
                    <TableCell className="text-xs font-medium text-sidebar-foreground">{a.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{a.entity}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{a.entity_type}</TableCell>
                    <TableCell>{a.acknowledged ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />}</TableCell>
                  </TableRow>
                ))}
                {alarmList.length === 0 && !alarms.isInitialLoading && (
                  <TableRow><TableCell colSpan={5} className="text-xs text-muted-foreground text-center py-4">No active alarms</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="events">
          <div className="rounded-lg border border-border overflow-hidden mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs w-12">Level</TableHead>
                  <TableHead className="text-xs">Message</TableHead>
                  <TableHead className="text-xs">Entity</TableHead>
                  <TableHead className="text-xs">User</TableHead>
                  <TableHead className="text-xs">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {eventList.map(e => (
                  <TableRow key={e.id}>
                    <TableCell><div className={cn("h-2 w-2 rounded-full", e.severity === "error" ? "bg-red-500" : e.severity === "warning" ? "bg-amber-500" : "bg-blue-500")} /></TableCell>
                    <TableCell className="text-xs text-sidebar-foreground max-w-[300px] truncate">{e.message}</TableCell>
                    <TableCell className="text-xs text-muted-foreground font-mono-code">{e.entity}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{e.username || "-"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{e.created_at ? new Date(e.created_at).toLocaleString() : "-"}</TableCell>
                  </TableRow>
                ))}
                {eventList.length === 0 && !events.isInitialLoading && (
                  <TableRow><TableCell colSpan={5} className="text-xs text-muted-foreground text-center py-4">No recent events</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      <AIAssistantPanel visible={assistantOpen} onToggle={() => setAssistantOpen(!assistantOpen)} />
    </div>
  )
}

function AssistantIcon({ className }: { className?: string }) {
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
