"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, AlertTriangle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

type ServiceStatus = "online" | "offline" | "degraded" | "checking" | "not_configured"

interface ServiceItem {
  label: string
  status: ServiceStatus
  message?: string
}

const TIMEOUT_MS = 8000

async function fetchWithTimeout(url: string, timeoutMs = TIMEOUT_MS): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { signal: controller.signal })
    clearTimeout(id)
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` }
    return { ok: true, data: await res.json() }
  } catch (e: unknown) {
    clearTimeout(id)
    return { ok: false, error: e instanceof Error && e.name === "AbortError" ? "Timeout" : (e instanceof Error ? e.message : "Unknown") }
  }
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.dclab.local"

export default function HealthPage() {
  const [services, setServices] = useState<ServiceItem[]>([
    { label: "FastAPI", status: "checking" },
    { label: "Agent Engine", status: "checking" },
    { label: "Postgres", status: "checking" },
    { label: "Redis", status: "checking" },
    { label: "vCenter", status: "checking" },
  ])
  const [globalError, setGlobalError] = useState<string | null>(null)

  const checkAll = async () => {
    setGlobalError(null)
    const results: ServiceItem[] = [
      { label: "FastAPI", status: "checking" },
      { label: "Agent Engine", status: "checking" },
      { label: "Postgres", status: "checking" },
      { label: "Redis", status: "checking" },
      { label: "vCenter", status: "checking" },
    ]

    // FastAPI health
    const fastapi = await fetchWithTimeout(`${BASE}/health`)
    results[0] = fastapi.ok ? { label: "FastAPI", status: "online", message: "API ready" } : { label: "FastAPI", status: "offline", message: fastapi.error }

    // Agent Engine health
    const agent = await fetchWithTimeout(`${BASE}/api/v1/agent/health`)
    if (agent.ok) {
      const d = agent.data as Record<string, unknown>
      results[1] = { label: "Agent Engine", status: d.status === "ok" || d.status === "online" ? "online" : "degraded", message: typeof d.message === "string" ? d.message : "Engine ready" }
    } else {
      results[1] = { label: "Agent Engine", status: "not_configured", message: `Agent endpoint: ${agent.error || "unavailable"}` }
    }

    // Postgres - try via health endpoint if available
    const pg = await fetchWithTimeout(`${BASE}/api/v1/storage/postgres/status`)
    if (pg.ok) {
      const d = pg.data as Record<string, unknown>
      results[2] = { label: "Postgres", status: d.status === "connected" || d.status === "online" ? "online" : "offline", message: typeof d.message === "string" ? d.message : (d.status as string || "Unknown") }
    } else {
      results[2] = { label: "Postgres", status: "not_configured", message: `Postgres status endpoint not available (${pg.error})` }
    }

    // Redis
    const redis = await fetchWithTimeout(`${BASE}/api/v1/storage/redis/status`)
    if (redis.ok) {
      const d = redis.data as Record<string, unknown>
      results[3] = { label: "Redis", status: d.status === "connected" || d.status === "online" ? "online" : "offline", message: typeof d.message === "string" ? d.message : (d.status as string || "Unknown") }
    } else {
      results[3] = { label: "Redis", status: "not_configured", message: `Redis status endpoint not available (${redis.error})` }
    }

    // vCenter
    const vcenter = await fetchWithTimeout(`${BASE}/api/v1/connections/vcenter/status`)
    if (vcenter.ok) {
      const d = vcenter.data as Record<string, unknown>
      results[4] = { label: "vCenter", status: d.configured ? (d.connected || d.status === "ok" ? "online" : "degraded") : "not_configured", message: d.configured ? (d as { message?: string }).message || `Connected to ${(d as { host?: string }).host || "vCenter"}` : "Not configured" }
    } else {
      results[4] = { label: "vCenter", status: "not_configured", message: `vCenter status endpoint unavailable (${vcenter.error})` }
    }

    setServices(results)
  }

  useEffect(() => { checkAll() }, [])

  const statusIcon = (s: ServiceStatus) => {
    if (s === "online") return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
    if (s === "offline") return <XCircle className="h-4 w-4 text-red-400" />
    if (s === "degraded") return <AlertTriangle className="h-4 w-4 text-amber-400" />
    if (s === "not_configured") return <AlertTriangle className="h-4 w-4 text-muted-foreground" />
    return <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />
  }

  const statusBadge = (s: ServiceStatus) => {
    if (s === "online") return <Badge className="bg-emerald-600/20 text-emerald-400 border-emerald-500/30">{statusIcon(s)}<span className="ml-1">Online</span></Badge>
    if (s === "offline") return <Badge variant="destructive">{statusIcon(s)}<span className="ml-1">Offline</span></Badge>
    if (s === "degraded") return <Badge className="bg-amber-600/20 text-amber-400 border-amber-500/30">{statusIcon(s)}<span className="ml-1">Degraded</span></Badge>
    if (s === "not_configured") return <Badge variant="secondary">{statusIcon(s)}<span className="ml-1">Not configured</span></Badge>
    return <Badge variant="secondary">{statusIcon(s)}<span className="ml-1">Checking</span></Badge>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">System Health</h1>
          <p className="text-xs text-muted-foreground">Service status and diagnostics</p>
        </div>
        <Button variant="outline" size="sm" onClick={checkAll}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />Refresh
        </Button>
      </div>

      {globalError && (
        <Card className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{globalError}</Card>
      )}

      <div className="grid gap-3 max-w-md">
        {services.map((item) => (
          <Card key={item.label} className="flex items-center justify-between border-border bg-card p-4">
            <div>
              <span className="text-sm font-medium">{item.label}</span>
              {item.message && <p className="text-[11px] text-muted-foreground mt-0.5">{item.message}</p>}
            </div>
            {statusBadge(item.status)}
          </Card>
        ))}
      </div>
    </div>
  )
}
