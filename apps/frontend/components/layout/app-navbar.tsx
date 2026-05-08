"use client"

import { useApiHealth } from "@/hooks/use-api-health"

export function AppNavbar() {
  const { status } = useApiHealth()

  const statusColor = status === "ok" ? "bg-emerald-500" : status === "degraded" ? "bg-amber-500" : "bg-red-500"
  const statusText = status === "ok" ? "online" : status === "degraded" ? "degraded" : "offline"

  return (
    <header className="fixed left-[260px] right-0 top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-card/80 backdrop-blur px-8">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-semibold text-foreground">
          Infrastructure Console
        </h1>
        <div className="flex items-center gap-1.5">
          <span className={cn("h-2 w-2 rounded-full", statusColor)} />
          <span className="text-xs text-muted-foreground">
            API {statusText}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-xs text-muted-foreground font-mono-code">
          v1.0.0
        </span>
      </div>
    </header>
  )
}

import { cn } from "@/lib/utils"
