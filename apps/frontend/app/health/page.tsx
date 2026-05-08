"use client"

import { useApiHealth } from "@/hooks/use-api-health"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react"

export default function HealthPage() {
  const { status } = useApiHealth()

  const items = [
    { label: "FastAPI", status: status },
    { label: "Agent Engine", status: "checking" as const },
    { label: "Postgres", status: "checking" as const },
    { label: "Redis", status: "checking" as const },
    { label: "vCenter", status: "checking" as const },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">System Health</h1>
        <p className="text-xs text-muted-foreground">Service status and diagnostics</p>
      </div>

      <div className="grid gap-3 max-w-md">
        {items.map((item) => (
          <Card key={item.label} className="flex items-center justify-between border-border bg-card p-4">
            <span className="text-sm font-medium">{item.label}</span>
            {item.status === "ok" && <Badge className="bg-emerald-600/20 text-emerald-400"><CheckCircle2 className="mr-1 h-3 w-3" />Online</Badge>}
            {item.status === "error" && <Badge variant="destructive"><XCircle className="mr-1 h-3 w-3" />Offline</Badge>}
            {item.status === "checking" && <Badge variant="secondary"><AlertTriangle className="mr-1 h-3 w-3" />Checking</Badge>}
          </Card>
        ))}
      </div>
    </div>
  )
}
